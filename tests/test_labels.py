import geopandas as gpd
from shapely.geometry import LineString

from roadwatch.data.grid import TileKey
from roadwatch.labels.osm import keep_empty_tile, rasterize_tile


def test_rasterize_tile_draws_road_in_right_place():
    key = TileKey(32644, 10.0, 512, 89, 356)
    x0, y0, x1, y1 = key.bounds()
    ymid = (y0 + y1) / 2
    roads = gpd.GeoDataFrame({"width_m": [8.0]}, geometry=[LineString([(x0, ymid), (x1, ymid)])],
                             crs=32644)
    m = rasterize_tile(roads, key)
    assert m.shape == (512, 512) and m.dtype.name == "uint8"
    rows = m.any(axis=1).nonzero()[0]
    assert 254 <= rows.mean() <= 258           # horizontal road at the vertical centre
    assert 1 <= len(rows) <= 3                 # ~10 m wide at 10 m pixels
    assert m[rows[0]].sum() == 512             # spans the whole tile


def test_empty_tile_road_free():
    key = TileKey(32644, 10.0, 512, 89, 356)
    roads = gpd.GeoDataFrame({"width_m": []}, geometry=[], crs=32644)
    assert rasterize_tile(roads, key).sum() == 0


def test_keep_empty_tile_ratio_and_determinism():
    ids = [f"T32644_10m_512_{i}_7" for i in range(5000)]
    kept = [keep_empty_tile(t, 0.2) for t in ids]
    assert kept == [keep_empty_tile(t, 0.2) for t in ids]
    assert 0.18 < sum(kept) / len(kept) < 0.22
    assert all(keep_empty_tile(t, 1.0) for t in ids[:100])
