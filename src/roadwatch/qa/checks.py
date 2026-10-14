"""Quality gates: CRS/grid, cloud/no-data, and multi-date registration (KPI-6, NT-4).

Each check returns a QAResult; a tile that fails is marked unreliable (abstain), never guessed.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from skimage.registration import phase_cross_correlation

from roadwatch.data.grid import TileKey


@dataclass(frozen=True)
class QAResult:
    check: str
    passed: bool
    value: float
    threshold: float
    detail: str = ""


def check_grid(crs: str, transform: tuple, shape: tuple[int, int], key: TileKey) -> QAResult:
    """Output must sit exactly on the tile grid: right CRS, origin, pixel size, shape."""
    from roadwatch.data.sentinel2 import tile_transform

    want = tuple(tile_transform(key))[:6]
    ok = (crs == f"EPSG:{key.epsg}" and np.allclose(transform, want, atol=1e-6)
          and tuple(shape) == (key.size_px, key.size_px))
    return QAResult("crs_grid", ok, 0.0 if ok else 1.0, 0.0,
                    "" if ok else f"crs={crs} transform={transform} shape={shape} want={want}")


def check_valid(valid_fraction: float, cloud_fraction: float, max_cloud: float) -> QAResult:
    """Abstain if too little clear data (cloud, shadow, no-data)."""
    bad = 1 - valid_fraction
    return QAResult("cloud_nodata", bad <= max_cloud, round(bad, 4), max_cloud,
                    f"mean scene cloud={cloud_fraction:.3f}")


def registration_shift_px(ref: np.ndarray, mov: np.ndarray, upsample: int = 20) -> float:
    """Sub-pixel shift magnitude between two single-band images (0 = no data ignored)."""
    mask = (ref > 0) & (mov > 0)
    if mask.mean() < 0.3:
        return float("nan")
    a = np.where(mask, ref, 0).astype(np.float32)
    b = np.where(mask, mov, 0).astype(np.float32)
    a -= a[mask].mean()
    b -= b[mask].mean()
    a[~mask] = 0
    b[~mask] = 0
    shift, _, _ = phase_cross_correlation(a, b, upsample_factor=upsample)
    return float(np.hypot(*shift))


def check_registration(ref: np.ndarray, mov: np.ndarray, max_px: float) -> QAResult:
    s = registration_shift_px(ref, mov)
    ok = bool(np.isfinite(s) and s <= max_px)
    return QAResult("registration", ok, round(s, 3) if np.isfinite(s) else -1.0, max_px,
                    "insufficient overlap" if not np.isfinite(s) else "")
