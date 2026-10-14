"""Spatial holdout split (PROJECT_PROMPT.md Section 6.1, Section 2 "Test set never changes").

Blocks are squares on ONE metric grid for all of India (EPSG:7755, India NSF LCC), so the
split does not depend on the AOI: a block is test for the pilot iff it is test for the
statewide run. A block's split comes from a seeded hash of its index — no randomness at
run time, no state to lose.

Any chip/tile (any resolution) is classified by geometry:
  test   — centroid in a test block and fully inside test blocks
  buffer — within `buffer_m` of a test block but not test (never trained or tuned on)
  val / train — from its centroid block's hash
"""

from __future__ import annotations

import hashlib
import math

import geopandas as gpd
from shapely.geometry import box
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from roadwatch.config import SplitConfig

SPLIT_CRS = "EPSG:7755"


def block_u(seed: int, bx: int, by: int) -> float:
    """Deterministic uniform [0,1) value for block (bx, by)."""
    h = hashlib.sha256(f"{seed}:{bx}:{by}".encode()).digest()
    return int.from_bytes(h[:8], "big") / 2**64


def block_split(bx: int, by: int, cfg: SplitConfig) -> str:
    u = block_u(cfg.seed, bx, by)
    if u < cfg.test_fraction:
        return "test"
    if u < cfg.test_fraction + cfg.val_fraction:
        return "val"
    return "train"


def blocks_frame(aoi_4326: BaseGeometry, cfg: SplitConfig) -> gpd.GeoDataFrame:
    """All split blocks intersecting the AOI, in SPLIT_CRS, with their split label."""
    aoi = gpd.GeoSeries([aoi_4326], crs="EPSG:4326").to_crs(SPLIT_CRS).iloc[0]
    s = cfg.block_size_m
    x0, y0, x1, y1 = aoi.bounds
    rows = []
    for bx in range(math.floor(x0 / s), math.ceil(x1 / s)):
        for by in range(math.floor(y0 / s), math.ceil(y1 / s)):
            g = box(bx * s, by * s, (bx + 1) * s, (by + 1) * s)
            if g.intersects(aoi):
                rows.append({"block_id": f"B{bx}_{by}", "bx": bx, "by": by,
                             "split": block_split(bx, by, cfg), "geometry": g})
    return gpd.GeoDataFrame(rows, geometry="geometry", crs=SPLIT_CRS)


def assign_splits(
    chips_4326: gpd.GeoDataFrame,
    cfg: SplitConfig,
    zones_4326: list[BaseGeometry] | None = None,
) -> gpd.GeoDataFrame:
    """Add a `split` column (train/val/test/zone_test/buffer) to any chip footprint frame.

    `zones_4326` (high-res evaluation zones) are holdout when cfg.zones_are_holdout:
    chips touching a zone -> "zone_test", chips within buffer_m of one -> "buffer".
    """
    chips = chips_4326.to_crs(SPLIT_CRS)
    s = cfg.block_size_m
    test_blocks = blocks_frame(chips_4326.union_all(), cfg)
    test_geom = unary_union(test_blocks.loc[test_blocks.split == "test"].geometry.tolist())
    zone_geom = None
    if cfg.zones_are_holdout and zones_4326:
        zone_geom = gpd.GeoSeries(zones_4326, crs="EPSG:4326").to_crs(SPLIT_CRS).union_all()
    holdout = unary_union([g for g in (test_geom, zone_geom) if g is not None and not g.is_empty])
    near_holdout = holdout.buffer(cfg.buffer_m) if not holdout.is_empty else holdout

    labels = []
    for g in chips.geometry:
        c = g.centroid
        base = block_split(math.floor(c.x / s), math.floor(c.y / s), cfg)
        if zone_geom is not None and g.intersects(zone_geom):
            labels.append("zone_test")
        elif base == "test" and g.difference(test_geom).area < 1e-6 * g.area:
            labels.append("test")
        elif not near_holdout.is_empty and g.intersects(near_holdout):
            labels.append("buffer")
        else:
            labels.append(base if base != "test" else "buffer")
    out = chips_4326.copy()
    out["split"] = labels
    return out
