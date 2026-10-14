"""OpenStreetMap road labels: extract from a Geofabrik .pbf, rasterise onto the tile grid.

Licence: (c) OpenStreetMap contributors, ODbL 1.0.
Note: OSM is a *current* snapshot, so labels match recent imagery best; using them on older
dates adds noise for roads built later (handled by OSM edit history in CP2).
"""

from __future__ import annotations

import hashlib

import geopandas as gpd
import numpy as np
import pyogrio
from rasterio.features import rasterize
from shapely.geometry import box
from shapely.geometry.base import BaseGeometry

from roadwatch.data.grid import TileKey
from roadwatch.data.sentinel2 import tile_transform

# approximate carriageway width (m) per OSM highway class; drives rasterisation buffer
ROAD_WIDTH_M = {
    "motorway": 14, "trunk": 12, "primary": 10, "secondary": 8, "tertiary": 7,
    "motorway_link": 7, "trunk_link": 7, "primary_link": 7, "secondary_link": 6, "tertiary_link": 6,
    "unclassified": 6, "residential": 6, "living_street": 5, "road": 6, "service": 5, "track": 4,
}
ROAD_CLASSES = tuple(ROAD_WIDTH_M)


def extract_roads(pbf_path: str, aoi_4326: BaseGeometry) -> gpd.GeoDataFrame:
    """Road lines (vehicle classes) intersecting the AOI, EPSG:4326."""
    gdf = pyogrio.read_dataframe(pbf_path, layer="lines", bbox=aoi_4326.bounds,
                                 columns=["osm_id", "name", "highway", "other_tags"])
    gdf = gdf[gdf.highway.isin(ROAD_CLASSES)].copy()
    gdf = gdf[gdf.intersects(aoi_4326)]
    gdf["width_m"] = gdf.highway.map(ROAD_WIDTH_M).astype(float)
    return gdf.set_crs(4326, allow_override=True).reset_index(drop=True)


def rasterize_tile(roads_utm: gpd.GeoDataFrame, key: TileKey, min_half_width_m: float = 5.0) -> np.ndarray:
    """uint8 mask (1 = road) on the tile grid. roads_utm must be in the tile's EPSG."""
    fp = box(*key.bounds())
    sub = roads_utm[roads_utm.intersects(fp)]
    n = key.size_px
    if sub.empty:
        return np.zeros((n, n), np.uint8)
    shapes = ((g.buffer(max(w / 2, min_half_width_m), cap_style="flat"), 1)
              for g, w in zip(sub.geometry, sub.width_m, strict=True))
    return rasterize(shapes, out_shape=(n, n), transform=tile_transform(key), fill=0,
                     all_touched=True, dtype="uint8")


def keep_empty_tile(tile_id: str, keep_ratio: float, seed: int = 1564) -> bool:
    """Deterministic subsampling of road-free tiles (lean rule data.empty_tile_keep_ratio)."""
    u = int(hashlib.sha256(f"{seed}:empty:{tile_id}".encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    return u < keep_ratio
