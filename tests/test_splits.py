import json

import geopandas as gpd
from shapely.geometry import box

from roadwatch.cli import HOLDOUT_DIR, _ids_hash
from roadwatch.config import CONFIG_DIR, GridConfig, SplitConfig, load_config
from roadwatch.data.grid import tiles_frame
from roadwatch.data.splits import SPLIT_CRS, assign_splits, block_split, blocks_frame


def test_block_split_is_deterministic():
    cfg = SplitConfig()
    assert [block_split(i, 7, cfg) for i in range(50)] == [block_split(i, 7, cfg) for i in range(50)]


def test_split_fraction_roughly_matches():
    cfg = SplitConfig()
    labels = [block_split(x, y, cfg) for x in range(60) for y in range(60)]
    frac = labels.count("test") / len(labels)
    assert 0.17 < frac < 0.23


def test_split_does_not_depend_on_aoi():
    cfg = SplitConfig()
    small = blocks_frame(box(80.5, 16.4, 80.9, 16.7), cfg)
    big = blocks_frame(box(79.5, 15.5, 81.5, 17.5), cfg)
    merged = small.merge(big[["block_id", "split"]], on="block_id", suffixes=("_s", "_b"))
    assert len(merged) == len(small)
    assert (merged.split_s == merged.split_b).all()


def test_no_train_chip_within_buffer_of_test():
    cfg = SplitConfig()
    aoi = box(80.0, 16.0, 81.5, 17.0)
    tiles = assign_splits(tiles_frame(aoi, GridConfig()), cfg)
    blocks = blocks_frame(aoi, cfg)
    test_area = blocks[blocks.split == "test"].union_all()
    train = tiles[tiles.split.isin(["train", "val"])].to_crs(SPLIT_CRS)
    assert len(train) > 0
    assert train.distance(test_area).min() >= cfg.buffer_m - 1e-6


def test_zones_are_holdout():
    cfg = SplitConfig()
    zone = box(80.60, 16.50, 80.70, 16.60)
    tiles = assign_splits(tiles_frame(box(80.4, 16.4, 80.9, 16.7), GridConfig()), cfg, [zone])
    touching = tiles[tiles.intersects(zone)]
    assert (touching.split == "zone_test").all()
    trainable = tiles[tiles.split.isin(["train", "val"])].to_crs(SPLIT_CRS)
    zone_m = gpd.GeoSeries([zone], crs=4326).to_crs(SPLIT_CRS).iloc[0]
    assert trainable.distance(zone_m).min() >= cfg.buffer_m - 1e-6


def test_frozen_holdout_unchanged():
    """The test set must never change (PROJECT_PROMPT.md Section 2)."""
    meta = json.loads((HOLDOUT_DIR / "holdout_meta.json").read_text(encoding="utf-8"))
    cfg = load_config(CONFIG_DIR / "statewide.yaml")
    assert cfg.split.model_dump() == meta["split"]
    blocks = blocks_frame(cfg.aoi.geometry(), cfg.split)
    ids = blocks.loc[blocks.split == "test", "block_id"].tolist()
    assert _ids_hash(ids) == meta["block_ids_sha256"]
    assert {z.name: list(z.bbox) for z in cfg.aoi.zones} == meta["holdout_zones"]
