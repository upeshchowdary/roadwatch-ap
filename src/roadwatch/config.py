"""Pydantic-validated project configuration.

Every lean-build rule (PROJECT_PROMPT.md Section 6.4) is a switch here, never hard-coded,
so Enhancement Mode (Section 14) can turn it off by editing YAML only.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "configs"

S2_BANDS = {"B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B09", "B11", "B12"}
S1_BANDS = {"vv", "vh"}


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Zone(_Strict):
    """A named high-resolution verification zone inside the AOI."""

    name: str
    bbox: tuple[float, float, float, float] = Field(description="lon_min, lat_min, lon_max, lat_max")
    description: str = ""

    @field_validator("bbox")
    @classmethod
    def _check_bbox(cls, v: tuple[float, float, float, float]):
        x0, y0, x1, y1 = v
        if not (-180 <= x0 < x1 <= 180 and -90 <= y0 < y1 <= 90):
            raise ValueError(f"invalid lon/lat bbox {v}")
        return v


class GridConfig(_Strict):
    resolution_m: float = 10.0
    tile_size_px: int = 512
    crs: str = "auto_utm"  # "auto_utm" = UTM zone of each tile's centre, or an explicit EPSG code


class AOIConfig(_Strict):
    name: str
    boundary: str = Field(description="path to a GeoJSON boundary, relative to repo root")
    zones: list[Zone] = []
    zones_extend_aoi: bool = True  # AOI = boundary ∪ zone boxes (a zone may cross a district line)
    grid: GridConfig = GridConfig()

    def geometry(self):
        """AOI polygon in EPSG:4326."""
        import geopandas as gpd
        from shapely.geometry import box
        from shapely.ops import unary_union

        geom = gpd.read_file(ROOT / self.boundary).to_crs("EPSG:4326").union_all()
        if self.zones_extend_aoi and self.zones:
            geom = unary_union([geom, *[box(*z.bbox) for z in self.zones]])
        return geom


class SplitConfig(_Strict):
    """Spatial holdout. Fixed at project start; identical for lean and every enhancement."""

    block_size_m: float = 20_480  # = 4 Sentinel-2 tiles of 512 px at 10 m
    test_fraction: float = Field(0.2, gt=0, lt=1)
    val_fraction: float = Field(0.1, ge=0, lt=1)
    buffer_m: float = Field(1_000, ge=0, description="gap around test blocks never used for training")
    seed: int = 1564
    zones_are_holdout: bool = True  # high-res/change zones are evaluation-only ("zone_test")


class DataConfig(_Strict):
    s2_bands: list[str] = ["B02", "B03", "B04", "B08"]
    s1_bands: list[str] = ["vv", "vh"]
    storage_dtype: Literal["uint8", "uint16"] = "uint8"
    temporal_mode: Literal["seasonal_composite", "all_scenes"] = "seasonal_composite"
    dates_per_year: int = Field(2, ge=1, le=52)
    date_start: str = "2022-01-01"
    date_end: str = "2026-12-31"
    empty_tile_keep_ratio: float = Field(0.2, ge=0, le=1)
    sampling: Literal["stratified", "random", "all"] = "stratified"
    stac_url: str = "https://planetarycomputer.microsoft.com/api/stac/v1"
    # season windows (MM-DD, MM-DD); dates_per_year picks the first N
    seasons: dict[str, tuple[str, str]] = {
        "pre_monsoon": ("03-01", "05-31"),
        "post_monsoon": ("10-15", "12-31"),
    }
    max_scenes_per_composite: int = Field(8, ge=1, description="least-cloudy scenes used per composite")
    scene_max_cloud_pct: float = Field(60.0, ge=0, le=100)
    reflectance_scale_max: float = 3000.0  # L2A reflectance (x1e4) mapped to 255 in uint8 storage

    @field_validator("s2_bands")
    @classmethod
    def _s2(cls, v: list[str]):
        bad = set(v) - S2_BANDS
        if bad:
            raise ValueError(f"unknown Sentinel-2 bands {bad}")
        return v

    @field_validator("s1_bands")
    @classmethod
    def _s1(cls, v: list[str]):
        bad = set(v) - S1_BANDS
        if bad:
            raise ValueError(f"unknown Sentinel-1 bands {bad}")
        return v


class ModelConfig(_Strict):
    backbone_mode: Literal["frozen_cached", "lora", "full_finetune"] = "frozen_cached"
    samroad_mode: Literal["off", "short_finetune", "full_finetune"] = "short_finetune"


class TrainConfig(_Strict):
    tune_subset_ratio: float = Field(0.2, gt=0, le=1)
    seeds: list[int] = [0, 1, 2]
    max_gpu_hours_without_asking: float = 8.0


class ChangeConfig(_Strict):
    prefilter_threshold: float = 0.15
    persistence_min_dates: int = Field(2, ge=1)
    min_length_m: float = 100.0


class QAConfig(_Strict):
    max_cloud_fraction: float = Field(0.3, ge=0, le=1)
    max_registration_error_px: float = 1.0


class InferConfig(_Strict):
    statewide_model: Literal["student", "teacher"] = "student"


class RoadWatchConfig(_Strict):
    aoi: AOIConfig
    split: SplitConfig = SplitConfig()
    data: DataConfig = DataConfig()
    model: ModelConfig = ModelConfig()
    train: TrainConfig = TrainConfig()
    change: ChangeConfig = ChangeConfig()
    qa: QAConfig = QAConfig()
    infer: InferConfig = InferConfig()

    @model_validator(mode="after")
    def _boundary_exists(self):
        if not (ROOT / self.aoi.boundary).exists():
            raise ValueError(f"AOI boundary file not found: {self.aoi.boundary}")
        return self

    def config_hash(self) -> str:
        """Short, stable hash of the full config; stamped on every output."""
        blob = json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(blob.encode()).hexdigest()[:12]


def load_config(path: str | Path = CONFIG_DIR / "pilot.yaml") -> RoadWatchConfig:
    """Load a top-level YAML. `include:` lists section files merged in order (later wins)."""
    path = Path(path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    merged: dict = {}
    for inc in raw.pop("include", []):
        part = yaml.safe_load((path.parent / inc).read_text(encoding="utf-8")) or {}
        _deep_merge(merged, part)
    _deep_merge(merged, raw)
    return RoadWatchConfig.model_validate(merged)


def _deep_merge(dst: dict, src: dict) -> None:
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _deep_merge(dst[k], v)
        else:
            dst[k] = v
