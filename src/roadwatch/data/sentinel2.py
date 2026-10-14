"""Sentinel-2 L2A: STAC search + windowed COG reads + cloud-masked seasonal composites.

Data is streamed per tile and never stored in full (PROJECT_PROMPT.md 1.1). Only the composite
for one 512x512 tile is held in memory; scene IDs are kept as pointers in the tile registry.

Radiometry: from processing baseline 04.00 (Jan 2022) L2A DN carry a +1000 offset
(BOA_ADD_OFFSET = -1000). We remove it so every date is on the same scale.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date

import numpy as np
import planetary_computer
import pystac
import rasterio
from pystac_client import Client
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.vrt import WarpedVRT
from shapely.geometry import box, mapping

from roadwatch.config import DataConfig
from roadwatch.data.grid import TileKey, _to_crs

log = logging.getLogger(__name__)

COLLECTION = "sentinel-2-l2a"
# SCL classes treated as invalid: 0 no data, 1 saturated, 3 cloud shadow, 8/9 cloud, 10 cirrus
SCL_INVALID = (0, 1, 3, 8, 9, 10)
BOA_OFFSET_BASELINE = "04.00"


@dataclass
class Composite:
    """One cloud-masked median composite for one tile and one season."""

    tile_id: str
    season: str
    year: int
    bands: list[str]
    data: np.ndarray                 # (bands, H, W) uint8 or uint16; 0 = no data
    valid_fraction: float            # share of pixels with >=1 clear observation
    cloud_fraction: float            # mean invalid share over the scenes used
    scene_ids: list[str] = field(default_factory=list)
    crs: str = ""
    transform: tuple = ()


def season_window(cfg: DataConfig, season: str, year: int) -> tuple[date, date]:
    s, e = cfg.seasons[season]
    start = date.fromisoformat(f"{year}-{s}")
    end = date.fromisoformat(f"{year}-{e}")
    return start, end


def search(bbox_4326: tuple[float, float, float, float], start: date, end: date,
           cfg: DataConfig) -> list[pystac.Item]:
    """Least-cloudy scenes first, capped at cfg.max_scenes_per_composite."""
    client = Client.open(cfg.stac_url, modifier=planetary_computer.sign_inplace)
    items = list(client.search(
        collections=[COLLECTION],
        intersects=mapping(box(*bbox_4326)),
        datetime=f"{start.isoformat()}/{end.isoformat()}",
        query={"eo:cloud_cover": {"lt": cfg.scene_max_cloud_pct}},
    ).items())
    items.sort(key=lambda it: it.properties.get("eo:cloud_cover", 100))
    return items[: cfg.max_scenes_per_composite]


def tile_transform(key: TileKey):
    x0, _, _, y1 = key.bounds()
    return from_origin(x0, y1, key.res_m, key.res_m)


def _read_asset(href: str, key: TileKey, resampling: Resampling) -> np.ndarray:
    """Read one band onto the tile grid (exact for same-zone S2; reprojects otherwise)."""
    with rasterio.open(href) as src:
        with WarpedVRT(src, crs=f"EPSG:{key.epsg}", transform=tile_transform(key),
                       width=key.size_px, height=key.size_px, resampling=resampling,
                       src_nodata=0, nodata=0) as vrt:
            return vrt.read(1)


def _boa_offset(item: pystac.Item) -> int:
    pb = str(item.properties.get("s2:processing_baseline", "00.00"))
    return 1000 if pb >= BOA_OFFSET_BASELINE else 0


def composite_tile(key: TileKey, season: str, year: int, cfg: DataConfig,
                   items: list[pystac.Item] | None = None) -> Composite:
    """Median of clear observations per pixel over the season's least-cloudy scenes."""
    start, end = season_window(cfg, season, year)
    fp = _to_crs(box(*key.bounds()), key.epsg, 4326)
    if items is None:
        items = search(fp.bounds, start, end, cfg)
    bands = cfg.s2_bands
    n = key.size_px
    stack, cloud_fracs, used = [], [], []
    for it in items:
        try:
            scl = _read_asset(it.assets["SCL"].href, key, Resampling.nearest)
        except Exception as e:  # noqa: BLE001 — a bad scene must not kill the tile
            log.warning("SCL read failed %s: %s", it.id, e)
            continue
        covered = scl != 0
        if covered.mean() < 0.05:
            continue  # scene does not actually cover this tile
        invalid = np.isin(scl, SCL_INVALID)
        cloud_fracs.append(float(invalid[covered].mean()))
        if invalid.all():
            continue
        off = _boa_offset(it)
        arr = np.zeros((len(bands), n, n), np.float32)
        for bi, b in enumerate(bands):
            dn = _read_asset(it.assets[b].href, key, Resampling.nearest).astype(np.float32)
            arr[bi] = np.clip(dn - off, 0, None)
        arr[:, invalid] = np.nan
        stack.append(arr)
        used.append(it.id)

    if stack:
        with np.errstate(all="ignore"):
            import warnings

            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                med = np.nanmedian(np.stack(stack), axis=0)
        valid = ~np.isnan(med).any(axis=0)
    else:
        med = np.full((len(bands), n, n), np.nan, np.float32)
        valid = np.zeros((n, n), bool)

    data = to_storage(med, cfg)
    return Composite(
        tile_id=key.tile_id, season=season, year=year, bands=list(bands), data=data,
        valid_fraction=float(valid.mean()),
        cloud_fraction=float(np.mean(cloud_fracs)) if cloud_fracs else 1.0,
        scene_ids=used, crs=f"EPSG:{key.epsg}", transform=tuple(tile_transform(key))[:6],
    )


def to_storage(refl: np.ndarray, cfg: DataConfig) -> np.ndarray:
    """Reflectance (x1e4, NaN = no data) -> storage dtype. 0 is reserved for no data."""
    nan = np.isnan(refl)
    if cfg.storage_dtype == "uint8":
        out = np.clip(np.nan_to_num(refl) / cfg.reflectance_scale_max * 254, 0, 254) + 1
        out = out.astype(np.uint8)
    else:
        out = (np.clip(np.nan_to_num(refl), 0, 65534) + 1).astype(np.uint16)
    out[nan] = 0
    return out


def write_geotiff(c: Composite, path) -> None:
    """Write a composite as a compressed, CRS-tagged GeoTIFF (for the data cache / QGIS)."""
    from affine import Affine

    profile = {
        "driver": "GTiff", "width": c.data.shape[2], "height": c.data.shape[1],
        "count": c.data.shape[0], "dtype": c.data.dtype.name, "crs": c.crs,
        "transform": Affine(*c.transform), "nodata": 0, "compress": "deflate",
        "tiled": True, "blockxsize": 256, "blockysize": 256,
    }
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(c.data)
        dst.descriptions = tuple(c.bands)
        dst.update_tags(tile_id=c.tile_id, season=c.season, year=str(c.year),
                        scenes=",".join(c.scene_ids), valid_fraction=f"{c.valid_fraction:.4f}")
