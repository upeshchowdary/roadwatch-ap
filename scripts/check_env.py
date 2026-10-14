"""Print PRESENT / MISSING for every key in .env.example. Never prints a value.

Usage: uv run python scripts/check_env.py [--strict]
  --strict  exit 1 if any CP1 key is missing
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
# Groups where any one key is enough
ANY_OF = {"KAGGLE": [["KAGGLE_API_TOKEN"], ["KAGGLE_USERNAME", "KAGGLE_KEY"]]}
NOT_SECRET = {"ROADWATCH_OFFLINE"}


def example_keys() -> tuple[list[str], set[str]]:
    keys, cp1, section = [], set(), ""
    for line in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
        if line.startswith("# ---"):
            section = line
        elif "=" in line and not line.startswith("#"):
            k = line.split("=", 1)[0].strip()
            keys.append(k)
            if "CP1" in section:
                cp1.add(k)
    return keys, cp1


def main() -> int:
    env_file = ROOT / ".env"
    values = dotenv_values(env_file) if env_file.exists() else {}
    keys, cp1 = example_keys()

    def present(k: str) -> bool:
        return bool((values.get(k) or os.environ.get(k) or "").strip())

    print(f".env file: {'found' if env_file.exists() else 'NOT FOUND (copy .env.example to .env)'}")
    missing_cp1 = []
    for k in keys:
        if k in NOT_SECRET:
            continue
        status = "PRESENT" if present(k) else "MISSING"
        tag = "CP1" if k in cp1 else "CP2"
        print(f"  [{tag}] {k:<28} {status}")
    for group, options in ANY_OF.items():
        ok = any(all(present(k) for k in opt) for opt in options)
        print(f"  => {group}: {'OK' if ok else 'MISSING'}")
        if not ok:
            missing_cp1.append(group)
    for k in cp1:
        if not any(k in sum(opts, []) for opts in ANY_OF.values()) and not present(k):
            missing_cp1.append(k)
    if missing_cp1:
        print(f"CP1 missing: {', '.join(sorted(set(missing_cp1)))}")
    else:
        print("CP1 keys: all present")
    return 1 if ("--strict" in sys.argv and missing_cp1) else 0


if __name__ == "__main__":
    sys.exit(main())
