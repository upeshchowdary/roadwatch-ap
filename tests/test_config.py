import pytest
from pydantic import ValidationError

from roadwatch.config import CONFIG_DIR, DataConfig, RoadWatchConfig, load_config


def test_pilot_and_statewide_configs_load():
    pilot = load_config(CONFIG_DIR / "pilot.yaml")
    state = load_config(CONFIG_DIR / "statewide.yaml")
    assert pilot.aoi.name == "ntr_krishna_pilot"
    assert len(pilot.aoi.zones) == 3
    # same lean switches and the same frozen split in both
    assert pilot.data == state.data
    assert pilot.split == state.split
    assert pilot.aoi.zones == state.aoi.zones


def test_lean_switches_are_config_not_code():
    cfg = load_config(CONFIG_DIR / "pilot.yaml")
    assert cfg.data.empty_tile_keep_ratio == 0.2
    assert cfg.data.s2_bands == ["B02", "B03", "B04", "B08"]
    assert cfg.model.backbone_mode == "frozen_cached"
    assert cfg.infer.statewide_model == "student"


def test_config_hash_is_stable_and_sensitive():
    a = load_config(CONFIG_DIR / "pilot.yaml")
    b = load_config(CONFIG_DIR / "pilot.yaml")
    assert a.config_hash() == b.config_hash()
    changed = a.model_copy(update={"data": DataConfig(empty_tile_keep_ratio=1.0)})
    assert changed.config_hash() != a.config_hash()


def test_unknown_band_rejected():
    with pytest.raises(ValidationError):
        DataConfig(s2_bands=["B02", "B99"])


def test_unknown_key_rejected():
    with pytest.raises(ValidationError):
        RoadWatchConfig.model_validate(
            {"aoi": {"name": "x", "boundary": "configs/boundaries/ntr_district.geojson"},
             "data": {"typo_key": 1}}
        )


def test_missing_boundary_rejected():
    with pytest.raises(ValidationError):
        RoadWatchConfig.model_validate({"aoi": {"name": "x", "boundary": "nope.geojson"}})
