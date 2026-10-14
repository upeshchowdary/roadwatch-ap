"""Disk guard (PROJECT_PROMPT.md Section 2, ADR-003).

Reports free space on the project drive and the size of the project, its env, caches and
the local data cache. Exits 1 if a limit is broken.

Usage: uv run python scripts/disk_check.py [--need-gb N]
  --need-gb N  also fail if a planned N GB download would break a limit
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIN_FREE_GB = 1.0          # never let the drive go below this
CODE_ENV_LIMIT_GB = 3.0    # repo + .venv + caches (ADR-003 option B)
DATA_CACHE_LIMIT_GB = 30.0 # git-ignored data_cache/ (ADR-003 option B)


def dir_gb(p: Path) -> float:
    if not p.exists():
        return 0.0
    total = 0
    for f in p.rglob("*"):
        try:
            if f.is_file() and not f.is_symlink():
                total += f.stat().st_size
        except OSError:
            pass
    return total / 1e9


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--need-gb", type=float, default=0.0)
    args = ap.parse_args()

    free = shutil.disk_usage(ROOT).free / 1e9
    data = dir_gb(ROOT / "data_cache")
    total = dir_gb(ROOT)
    code_env = total - data
    parts = {p: dir_gb(ROOT / p) for p in (".venv", ".cache", "web/node_modules", "data_cache")}

    print(f"drive free        : {free:8.2f} GB  (min {MIN_FREE_GB} GB)")
    print(f"project total     : {total:8.2f} GB")
    for p, gb in parts.items():
        print(f"  {p:<16}: {gb:8.2f} GB")
    print(f"code+env+caches   : {code_env:8.2f} GB  (limit {CODE_ENV_LIMIT_GB} GB)")
    print(f"data_cache        : {data:8.2f} GB  (limit {DATA_CACHE_LIMIT_GB} GB)")

    problems = []
    if free - args.need_gb < MIN_FREE_GB:
        problems.append(f"drive would drop below {MIN_FREE_GB} GB free")
    if code_env > CODE_ENV_LIMIT_GB:
        problems.append(f"code+env {code_env:.2f} GB > {CODE_ENV_LIMIT_GB} GB")
    if data + args.need_gb > DATA_CACHE_LIMIT_GB:
        problems.append(f"data_cache would reach {data + args.need_gb:.2f} GB > {DATA_CACHE_LIMIT_GB} GB")
    for p in problems:
        print(f"WARNING: {p}")
    print("disk OK" if not problems else "disk check FAILED")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
