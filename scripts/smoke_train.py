"""CPU smoke test for kaggle/<model>/train.py on synthetic DeepGlobe-like data.

Catches crashes before spending Kaggle GPU quota. Run with the smoke venv (torch CPU):
  data_cache/smoke_venv/Scripts/python.exe scripts/smoke_train.py baseline_a
Exercises: multi-crop training, val_every, early-stop bookkeeping, test eval with per-image
CSVs, ONNX export, and resume from ckpt_last.pt.
"""

from __future__ import annotations

import os
import pprint
import re
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def make_data(root: Path, n: int = 24, size: int = 256) -> None:
    rng = np.random.default_rng(0)
    (root / "train").mkdir(parents=True, exist_ok=True)
    rows = ["image_id,split,sat_image_path,mask_path"]
    for i in range(n):
        img = rng.integers(0, 255, (size, size, 3), dtype=np.uint8)
        m = np.zeros((size, size), np.uint8)
        r = int(rng.integers(20, size - 20))
        m[r - 4:r + 4, :] = 255
        img[m > 0] = 200
        cv2.imwrite(str(root / "train" / f"{i}_sat.jpg"), img)
        cv2.imwrite(str(root / "train" / f"{i}_mask.png"), m)
        rows.append(f"{i},train,train/{i}_sat.jpg,train/{i}_mask.png")
    (root / "metadata.csv").write_text("\n".join(rows) + "\n")


def run(model: str, cfg: dict, out: Path, data: Path) -> subprocess.CompletedProcess:
    src = (ROOT / "kaggle" / model / "train.py").read_text(encoding="utf-8")
    block = "RUN_CONFIG = " + pprint.pformat(cfg, sort_dicts=False) + "\n"
    src = re.sub(r"RUN_CONFIG = \{.*?\n\}\n", lambda _: block, src, count=1, flags=re.S)
    script = out / "train_smoke.py"
    script.write_text(src.replace('os.path.abspath("./out")', repr(str(out / "work"))),
                      encoding="utf-8")
    env = {**os.environ, "ROADWATCH_DATA_ROOT": str(data), "PYTHONIOENCODING": "utf-8"}
    return subprocess.run([sys.executable, str(script)], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=env, timeout=1200)


def main() -> int:
    model = sys.argv[1] if len(sys.argv) > 1 else "baseline_a"
    base = ROOT / "data_cache" / "smoke" / model
    data = base / "data"
    make_data(data)
    cfg = {
        "run_id": "smoke", "arch": "Unet", "encoder": "resnet34", "encoder_weights": None,
        "epochs": 3, "timing_only": False, "seed": 0, "crop": 128, "batch_size": 8,
        "crops_per_image": 4, "lr": 3e-4, "weight_decay": 1e-4, "subset_ratio": 1.0,
        "patience": 3, "val_every": 2, "num_workers": 0, "max_train_batches": 2,
        "eval_test": True, "export_onnx": True, "resume_dir": "", "max_hours": 3.0,
        "config_hash": "smoke",
    }
    import shutil

    shutil.rmtree(base / "work", ignore_errors=True)
    # 1) run 2 epochs, 2) resume to epoch 3 (resume path)
    r1 = run(model, {**cfg, "epochs": 2, "export_onnx": False}, base, data)
    print(r1.stdout[-1500:], r1.stderr[-3000:])
    if r1.returncode:
        return 1
    r2 = run(model, cfg, base, data)
    print(r2.stdout[-2500:], r2.stderr[-3000:])
    if r2.returncode:
        return 1
    work = base / "work"
    need = ["ckpt_last.pt", "ckpt_best.pt", "train_log.csv", "timing.json", "metrics.json",
            "per_image_val.csv", "per_image_test.csv", "model_best.onnx"]
    missing = [f for f in need if not (work / f).exists()]
    resumed = "resumed from" in r2.stdout
    print(f"missing={missing} resumed={resumed}")
    return 0 if not missing and resumed else 1


if __name__ == "__main__":
    sys.exit(main())
