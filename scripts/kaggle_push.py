"""Build and push a Kaggle kernel run from kaggle/<model>/runs.yaml.

Usage:
  uv run --extra kaggle --env-file .env python scripts/kaggle_push.py baseline_a timing [--dry-run]
  uv run --extra kaggle --env-file .env python scripts/kaggle_push.py baseline_a timing --status
  uv run --extra kaggle --env-file .env python scripts/kaggle_push.py baseline_a timing --fetch

- Injects the run config into the script, stamps a config hash, writes kernel-metadata.json
  into kaggle/build/<model>_<run>/ (git-ignored) and runs `kaggle kernels push`.
- Appends a row to runs/RUN_LOG.csv (contribution evidence).
- --fetch downloads outputs to data_cache/runs/<model>_<run>/ (git-ignored).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import pprint
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
RUN_LOG = ROOT / "runs" / "RUN_LOG.csv"


def kaggle(*args: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    return subprocess.run([sys.executable, "-m", "kaggle", *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=600, env=env)


def build(model: str, run: str) -> tuple[Path, dict, dict]:
    spec = yaml.safe_load((ROOT / "kaggle" / model / "runs.yaml").read_text(encoding="utf-8"))
    cfg = {**spec["defaults"], **spec["runs"][run]}
    cfg_hash = hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12]
    cfg["run_id"] = f"{model}_{run}_{cfg_hash}"
    cfg["config_hash"] = cfg_hash

    src = (ROOT / "kaggle" / model / "train.py").read_text(encoding="utf-8")
    block = "RUN_CONFIG = " + pprint.pformat(cfg, sort_dicts=False) + "\n"
    new_src, n = re.subn(r"RUN_CONFIG = \{.*?\n\}\n", lambda _: block, src, count=1, flags=re.S)
    if n != 1:
        raise RuntimeError("RUN_CONFIG block not found in train.py")

    user = os.environ.get("KAGGLE_USERNAME")
    if not user:
        raise RuntimeError("KAGGLE_USERNAME missing (.env)")
    k = spec["kernel"]
    slug = f"{k['title_prefix']}-{run}".replace("_", "-")
    out = ROOT / "kaggle" / "build" / f"{model}_{run}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "train.py").write_text(new_src, encoding="utf-8")
    meta = {
        "id": f"{user}/{slug}",
        "title": slug,
        "code_file": "train.py",
        "language": "python",
        "kernel_type": "script",
        "is_private": k["is_private"],
        "enable_gpu": True,
        "enable_tpu": False,
        "enable_internet": k["enable_internet"],
        "dataset_sources": k["dataset_sources"],
        "competition_sources": [],
        "kernel_sources": [],
        "model_sources": [],
        "machine_shape": k["accelerator"],
    }
    (out / "kernel-metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return out, cfg, meta


def log_run(cfg: dict, meta: dict, result: str) -> None:
    with RUN_LOG.open("a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([cfg["run_id"], os.environ.get("ROADWATCH_PERSON", "lead"),
                                meta["id"].split("/")[0], meta["id"], cfg["config_hash"],
                                datetime.now(UTC).isoformat(timespec="seconds"), "", "", result, ""])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("run")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--fetch", action="store_true")
    a = ap.parse_args()

    out, cfg, meta = build(a.model, a.run)
    if a.status:
        r = kaggle("kernels", "status", meta["id"])
        print((r.stdout + r.stderr).strip())
        return r.returncode
    if a.fetch:
        dest = ROOT / "data_cache" / "runs" / f"{a.model}_{a.run}"
        dest.mkdir(parents=True, exist_ok=True)
        r = kaggle("kernels", "output", meta["id"], "-p", str(dest), "-o")
        print((r.stdout + r.stderr).strip()[-2000:])
        print(f"outputs -> {dest}")
        return r.returncode
    print(f"run_id={cfg['run_id']}  kernel={meta['id']}  build={out.relative_to(ROOT)}")
    if a.dry_run:
        return 0
    r = kaggle("kernels", "push", "-p", str(out), "--accelerator", meta["machine_shape"])
    print((r.stdout + r.stderr).strip())
    log_run(cfg, meta, "pushed" if r.returncode == 0 else "push_failed")
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
