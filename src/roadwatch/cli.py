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
