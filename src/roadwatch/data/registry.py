"""Tile registry + reserve log (PROJECT_PROMPT.md Section 6.5): nothing cut is ever lost.

One row per (tile_id, sensor, date_key). Rows store POINTERS (scene IDs), never imagery, so a
reserved item can be re-fetched later at full quality (16-bit, all bands) by Enhancement Mode.

status = included | reserved; reserve_reason in RESERVE_REASONS.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from roadwatch.config import ROOT

REGISTRY_PATH = ROOT / "evidence" / "tile_registry.parquet"
RESERVE_REASONS = {
    "empty_tile", "band_dropped", "cloudy", "prefilter_skipped", "subsampled", "extra_date",
    "qa_failed", "holdout_buffer",
}
S2_ALL_BANDS = ["B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B09", "B11", "B12"]
COLUMNS = [
    "tile_id", "sensor", "date_key", "epsg", "col", "row", "split", "zone", "stratum",
    "scene_ids", "bands_used", "bands_reserved", "storage_dtype", "valid_fraction",
    "cloud_fraction", "qa_pass", "has_road", "status", "reserve_reason", "local_path",
    "config_hash", "updated_utc",
]


def load(path: Path = REGISTRY_PATH) -> pd.DataFrame:
    if path.exists():
        return pd.read_parquet(path)
    return pd.DataFrame(columns=COLUMNS)


def upsert(rows: list[dict], path: Path = REGISTRY_PATH) -> pd.DataFrame:
    """Insert or replace rows keyed by (tile_id, sensor, date_key). Never deletes others."""
    for r in rows:
        if r.get("status") == "reserved" and r.get("reserve_reason") not in RESERVE_REASONS:
            raise ValueError(f"bad reserve_reason {r.get('reserve_reason')!r}")
        r.setdefault("updated_utc", datetime.now(UTC).isoformat(timespec="seconds"))
    new = pd.DataFrame(rows, columns=COLUMNS)
    old = load(path)
    key = ["tile_id", "sensor", "date_key"]
    if len(old):
        merged = old.set_index(key)
        merged = merged[~merged.index.isin(new.set_index(key).index)].reset_index()
        df = pd.concat([merged, new], ignore_index=True) if len(merged) else new
    else:
        df = new
    df = df.sort_values(key).reset_index(drop=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    return df


def summary(df: pd.DataFrame) -> pd.DataFrame:
    return (df.assign(reason=df.reserve_reason.fillna(""))
              .groupby(["date_key", "status", "reason"]).size().rename("n").reset_index())
