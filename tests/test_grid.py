from shapely.geometry import box

from roadwatch.config import GridConfig
from roadwatch.data.grid import TileKey, iter_tiles, tiles_frame, utm_epsg


def test_utm_epsg():
    assert utm_epsg(80.6, 16.5) == 32644  # Vijayawada
    assert utm_epsg(77.0, 14.0) == 32643  # Anantapur
    assert utm_epsg(84.5, 18.7) == 32645  # Srikakulam tip


def test_tile_id_roundtrip():
    k = TileKey(32644, 10.0, 512, 81, 356)
    assert k.tile_id == "T32644_10m_512_81_356"
    assert TileKey.parse(k.tile_id) == k
    k2 = TileKey(32644, 0.5, 1024, -3, 7)
    assert TileKey.parse(k2.tile_id) == k2


def test_tile_ids_do_not_depend_on_aoi():
    grid = GridConfig()
    small = box(80.60, 16.50, 80.65, 16.55)
    big = box(80.50, 16.40, 80.80, 16.70)
    small_ids = {k.tile_id for k, _ in iter_tiles(small, grid)}
    big_ids = {k.tile_id for k, _ in iter_tiles(big, grid)}
    assert small_ids and small_ids <= big_ids


def test_tiles_cover_aoi():
    aoi = box(80.60, 16.50, 80.70, 16.60)
    tiles = tiles_frame(aoi, GridConfig())
    assert tiles.union_all().contains(aoi.buffer(-1e-6))
    assert tiles.tile_id.is_unique


def test_auto_utm_splits_across_zones():
    aoi = box(83.9, 18.0, 84.1, 18.1)  # straddles the 84E UTM boundary
    tiles = tiles_frame(aoi, GridConfig())
    assert set(tiles.epsg) == {32644, 32645}
