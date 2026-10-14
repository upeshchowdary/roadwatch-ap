"""`uv run roadwatch <stage> --config ...` — one command per pipeline stage."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import geopandas as gpd
import typer

from roadwatch.config import ROOT, load_config

app = typer.Typer(no_args_is_help=True, add_completion=False)
holdout_app = typer.Typer(no_args_is_help=True, help="Frozen spatial holdout (test blocks).")
app.add_typer(holdout_app, name="holdout")

DEFAULT_CFG = ROOT / "configs" / "pilot.yaml"
HOLDOUT_DIR = ROOT / "evidence" / "holdout"


def _aoi_geom(cfg):
    return cfg.aoi.geometry()


def _zone_geoms(cfg):
    from shapely.geometry import box

    return [box(*z.bbox) for z in cfg.aoi.zones]


@app.command()
def info(config: Path = DEFAULT_CFG) -> None:
    """Validate a config and print AOI, zones, tile and split counts."""
    from roadwatch.data.grid import tiles_frame
    from roadwatch.data.splits import assign_splits

    cfg = load_config(config)
    aoi = _aoi_geom(cfg)
    area = gpd.GeoSeries([aoi], crs=4326).to_crs("EPSG:7755").area.iloc[0] / 1e6
    tiles = assign_splits(tiles_frame(aoi, cfg.aoi.grid), cfg.split, _zone_geoms(cfg))
    typer.echo(f"config      : {config.name}  hash={cfg.config_hash()}")
    typer.echo(f"aoi         : {cfg.aoi.name}  area={area:,.0f} km2")
    typer.echo(f"grid        : {cfg.aoi.grid.tile_size_px}px @ {cfg.aoi.grid.resolution_m} m, "
               f"crs={cfg.aoi.grid.crs}  tiles={len(tiles)}  epsg={sorted(tiles.epsg.unique())}")
    typer.echo(f"splits      : {tiles.split.value_counts().to_dict()}")
    for z in cfg.aoi.zones:
        from shapely.geometry import box

        zb = box(*z.bbox)
        inside = zb.intersection(aoi).area / zb.area
        zt = tiles[tiles.intersects(zb)]
        typer.echo(f"zone {z.name:<26} in-AOI={inside:5.1%}  tiles={len(zt):3d}  "
                   f"splits={zt.split.value_counts().to_dict()}")


@app.command("s2-build")
def s2_build(
    config: Path = DEFAULT_CFG,
    zones_only: bool = typer.Option(True, help="only the high-res zones (False = whole AOI)"),
    zone: str = typer.Option("", help="restrict to one zone name prefix, e.g. A"),
    years: str = typer.Option("2022-2026", help="year range, e.g. 2022-2026"),
    out_dir: Path = ROOT / "data_cache" / "s2",
) -> None:
    """Build cloud-masked seasonal Sentinel-2 composites; log every tile in the registry."""
    import logging
    from datetime import date

    from shapely.geometry import box

    from roadwatch.data import registry
    from roadwatch.data.grid import TileKey, tiles_frame
    from roadwatch.data.sentinel2 import composite_region, season_window, write_geotiff
    from roadwatch.data.splits import assign_splits
    from roadwatch.qa.checks import check_grid, check_valid

    logging.basicConfig(level=logging.WARNING)
    cfg = load_config(config)
    tiles = assign_splits(tiles_frame(_aoi_geom(cfg), cfg.aoi.grid), cfg.split, _zone_geoms(cfg))
    tiles["zone"] = ""
    for z in cfg.aoi.zones:
        tiles.loc[tiles.intersects(box(*z.bbox)), "zone"] = z.name
    if zones_only:
        tiles = tiles[tiles.zone != ""]
    if zone:
        tiles = tiles[tiles.zone.str.startswith(zone)]
    groups = (tiles.groupby("zone") if zones_only else
              tiles.groupby([tiles.epsg, tiles.col // 5, tiles.row // 5]))
    y0, y1 = (int(y) for y in years.split("-"))
    seasons = list(cfg.data.seasons)[: cfg.data.dates_per_year]
    reserved_bands = [b for b in registry.S2_ALL_BANDS if b not in cfg.data.s2_bands]
    today, h = date.today(), cfg.config_hash()

    for gname, g in groups:
        keys = [TileKey.parse(t) for t in g.tile_id]
        for year in range(y0, y1 + 1):
            for season in seasons:
                if season_window(cfg.data, season, year)[1] > today:
                    continue  # season not finished yet
                date_key = f"{year}_{season}"
                d = out_dir / date_key
                todo = [k for k in keys if not (d / f"{k.tile_id}.tif").exists()]
                if not todo:
                    continue
                d.mkdir(parents=True, exist_ok=True)
                comps = composite_region(todo, season, year, cfg.data)
                rows = []
                for c, k in zip(comps, todo, strict=True):
                    qa_grid = check_grid(c.crs, c.transform, c.data.shape[1:], k)
                    qa_valid = check_valid(c.valid_fraction, c.cloud_fraction, cfg.qa.max_cloud_fraction)
                    path = d / f"{k.tile_id}.tif"
                    write_geotiff(c, path)
                    meta = tiles.set_index("tile_id").loc[k.tile_id]
                    ok = qa_grid.passed and qa_valid.passed
                    rows.append({
                        "tile_id": k.tile_id, "sensor": "s2", "date_key": date_key,
                        "epsg": k.epsg, "col": k.col, "row": k.row, "split": meta.split,
                        "zone": meta.zone, "stratum": None, "scene_ids": ",".join(c.scene_ids),
                        "bands_used": ",".join(c.bands), "bands_reserved": ",".join(reserved_bands),
                        "storage_dtype": cfg.data.storage_dtype,
                        "valid_fraction": round(c.valid_fraction, 4),
                        "cloud_fraction": round(c.cloud_fraction, 4), "qa_pass": ok,
                        "has_road": None, "status": "included" if ok else "reserved",
                        "reserve_reason": None if ok else ("cloudy" if not qa_valid.passed else "qa_failed"),
                        "local_path": str(path.relative_to(ROOT)), "config_hash": h,
                    })
                registry.upsert(rows)
                n_ok = sum(r["qa_pass"] for r in rows)
                typer.echo(f"{gname} {date_key}: {len(rows)} tiles, {n_ok} pass QA, "
                           f"scenes={len(comps[0].scene_ids) if comps else 0}")


@holdout_app.command("freeze")
def holdout_freeze(config: Path = ROOT / "configs" / "statewide.yaml",
                   force: bool = typer.Option(False, help="overwrite an existing frozen holdout")) -> None:
    """Write the statewide test-block list once. Refuses to overwrite unless --force."""
    from roadwatch.data.splits import blocks_frame

    out = HOLDOUT_DIR / "test_blocks.geojson"
    if out.exists() and not force:
        raise typer.BadParameter(f"{out} already frozen; the test set must never change.")
    cfg = load_config(config)
    blocks = blocks_frame(_aoi_geom(cfg), cfg.split)
    test = blocks[blocks.split == "test"].sort_values("block_id").reset_index(drop=True)
    HOLDOUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = test.to_crs("EPSG:4326")[["block_id", "bx", "by", "geometry"]].to_json()
    out.write_text(payload, encoding="utf-8")
    meta = {
        "frozen_on": "2026-10-14",
        "aoi": cfg.aoi.name,
        "split": cfg.split.model_dump(),
        "n_blocks_total": int(len(blocks)),
        "n_test_blocks": int(len(test)),
        "holdout_zones": {z.name: list(z.bbox) for z in cfg.aoi.zones} if cfg.split.zones_are_holdout else {},
        "block_ids_sha256": _ids_hash(test.block_id.tolist()),
    }
    (HOLDOUT_DIR / "holdout_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    typer.echo(json.dumps(meta, indent=2))


@holdout_app.command("check")
def holdout_check(config: Path = ROOT / "configs" / "statewide.yaml") -> None:
    """Recompute test blocks from config and verify they equal the frozen list."""
    from roadwatch.data.splits import blocks_frame

    meta = json.loads((HOLDOUT_DIR / "holdout_meta.json").read_text(encoding="utf-8"))
    cfg = load_config(config)
    blocks = blocks_frame(_aoi_geom(cfg), cfg.split)
    ids = sorted(blocks.loc[blocks.split == "test", "block_id"])
    if _ids_hash(ids) != meta["block_ids_sha256"]:
        typer.echo("HOLDOUT CHANGED — test blocks differ from the frozen list!", err=True)
        raise typer.Exit(1)
    typer.echo(f"holdout OK: {len(ids)} test blocks match frozen hash {meta['block_ids_sha256'][:12]}")


def _ids_hash(ids: list[str]) -> str:
    return hashlib.sha256("\n".join(sorted(ids)).encode()).hexdigest()


if __name__ == "__main__":
    app()
