import pytest

from roadwatch.data import registry


def _row(tile, date_key, status="included", reason=None, valid=1.0):
    return {"tile_id": tile, "sensor": "s2", "date_key": date_key, "status": status,
            "reserve_reason": reason, "valid_fraction": valid}


def test_upsert_replaces_by_key_and_keeps_others(tmp_path):
    p = tmp_path / "reg.parquet"
    registry.upsert([_row("T1", "2023_pre"), _row("T2", "2023_pre")], p)
    df = registry.upsert([_row("T1", "2023_pre", valid=0.5), _row("T1", "2024_pre")], p)
    assert len(df) == 3
    assert df.set_index(["tile_id", "date_key"]).loc[("T1", "2023_pre"), "valid_fraction"] == 0.5


def test_reserved_needs_known_reason(tmp_path):
    p = tmp_path / "reg.parquet"
    registry.upsert([_row("T1", "d", "reserved", "cloudy")], p)
    with pytest.raises(ValueError):
        registry.upsert([_row("T2", "d", "reserved", "because")], p)
