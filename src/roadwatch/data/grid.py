"""Deterministic tile grid (PROJECT_PROMPT.md Section 6.5).

Tiles live on a per-UTM-zone grid anchored at the projection origin, so a tile's ID depends
only on (EPSG, resolution, tile size, column, row) — never on which AOI asked for it.
The same tile therefore gets the same ID for a district, a state, or all of India.
"""

from __future__ import annotations

import math
from collections.abc import Iterator
from dataclasses import dataclass

import geopandas as gpd
import shapely
from pyproj import CRS, Transformer
from shapely.geometry import box
from shapely.geometry.base import BaseGeometry

from roadwatch.config import GridConfig


def utm_epsg(lon: float, lat: float) -> int:
    """EPSG code of the WGS84 UTM zone containing (lon, lat)."""
    zone = min(int((lon + 180) // 6) + 1, 60)
    return (32600 if lat >= 0 else 32700) + zone


def utm_zone_lon_bounds(epsg: int) -> tuple[float, float]:
    zone = epsg % 100
    west = -180 + (zone - 1) * 6
    return west, west + 6


@dataclass(frozen=True)
class TileKey:
    epsg: int
    res_m: float
    size_px: int
    col: int
    row: int

    @property
    def extent_m(self) -> float:
        return self.res_m * self.size_px

    @property
    def tile_id(self) -> str:
        res = f"{self.res_m:g}".replace(".", "p")
        return f"T{self.epsg}_{res}m_{self.size_px}_{self.col}_{self.row}"

    def bounds(self) -> tuple[float, float, float, float]:
        """(xmin, ymin, xmax, ymax) in the tile's UTM CRS. Row increases northwards."""
        e = self.extent_m
        return self.col * e, self.row * e, (self.col + 1) * e, (self.row + 1) * e

    @classmethod
    def parse(cls, tile_id: str) -> TileKey:
        epsg, res, size, col, row = tile_id[1:].split("_")
        return cls(int(epsg), float(res[:-1].replace("p", ".")), int(size), int(col), int(row))


def _to_crs(geom: BaseGeometry, src: int | str, dst: int | str) -> BaseGeometry:
    tr = Transformer.from_crs(CRS.from_user_input(src), CRS.from_user_input(dst), always_xy=True)
    return shapely.transform(geom, tr.transform, interleaved=False)


def iter_tiles(aoi_4326: BaseGeometry, grid: GridConfig) -> Iterator[tuple[TileKey, BaseGeometry]]:
    """Yield every grid tile intersecting the AOI, with its footprint in EPSG:4326.

    With crs="auto_utm" the AOI is cut into UTM longitude bands and each band is tiled
    in its own zone, like Sentinel-2 MGRS tiles.
    """
    if grid.crs == "auto_utm":
        lon0, lat0, lon1, lat1 = aoi_4326.bounds
        epsgs = sorted({utm_epsg(lon, (lat0 + lat1) / 2) for lon in _frange(lon0, lon1, 1.0)})
    else:
        epsgs = [CRS.from_user_input(grid.crs).to_epsg()]

    for epsg in epsgs:
        part = aoi_4326
        if grid.crs == "auto_utm":
            w, e = utm_zone_lon_bounds(epsg)
            part = aoi_4326.intersection(box(w, -90, e, 90))
            if part.is_empty:
                continue
        part_utm = _to_crs(part, 4326, epsg)
        ext = grid.resolution_m * grid.tile_size_px
        x0, y0, x1, y1 = part_utm.bounds
        for col in range(math.floor(x0 / ext), math.ceil(x1 / ext)):
            for row in range(math.floor(y0 / ext), math.ceil(y1 / ext)):
                key = TileKey(epsg, grid.resolution_m, grid.tile_size_px, col, row)
                fp = box(*key.bounds())
                if fp.intersects(part_utm):
                    yield key, _to_crs(fp, epsg, 4326)


def tiles_frame(aoi_4326: BaseGeometry, grid: GridConfig) -> gpd.GeoDataFrame:
    rows = [
        {"tile_id": k.tile_id, "epsg": k.epsg, "col": k.col, "row": k.row, "geometry": g}
        for k, g in iter_tiles(aoi_4326, grid)
    ]
    return gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")


def _frange(a: float, b: float, step: float) -> Iterator[float]:
    x = a
    while x < b:
        yield x
        x += step
    yield b
