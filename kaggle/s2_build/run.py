"""RoadWatch AP — Sentinel-2 composite build on a Kaggle CPU session (no GPU quota used).

Clones the public repo at a pinned commit, runs `roadwatch s2-build` for each zone in parallel
processes (network-bound), writes GeoTIFFs + registry rows to /kaggle/working.
Push with: scripts/kaggle_push.py s2_build zones
"""

# --- RUN_CONFIG (injected by scripts/kaggle_push.py; do not edit by hand) ---
RUN_CONFIG = {
    "run_id": "local-debug",
    "commit": "main",
    "config": "configs/pilot.yaml",
    "zones": ["A", "B", "C"],
    "years": "2022-2026",
    "config_hash": "none",
}
# --- END RUN_CONFIG ---

import glob
import os
import shutil
import subprocess
import sys
import time

REPO = "https://github.com/upeshchowdary/roadwatch-ap"
WORK = "/kaggle/working"
SRC = "/kaggle/temp/rw"
C = RUN_CONFIG
T0 = time.time()


def sh(cmd, **kw):
    print("+", " ".join(cmd), flush=True)
    return subprocess.run(cmd, check=True, **kw)


def main():
    if os.path.exists(SRC):
        shutil.rmtree(SRC)
    sh(["git", "clone", "-q", REPO, SRC])
    sh(["git", "-C", SRC, "checkout", "-q", C["commit"]])
    sh([sys.executable, "-m", "pip", "install", "-q", "pystac-client", "planetary-computer",
        "rasterio", "geopandas", "pyogrio", "typer", "pydantic>=2.7", "scikit-image"])
    env = {**os.environ, "PYTHONPATH": os.path.join(SRC, "src"), "PYTHONUNBUFFERED": "1"}
    procs = []
    for z in C["zones"]:
        e = {**env, "ROADWATCH_REGISTRY": os.path.join(WORK, f"registry_{z}.parquet")}
        log = open(os.path.join(WORK, f"log_{z}.txt"), "w")
        procs.append((z, subprocess.Popen(
            [sys.executable, "-m", "roadwatch.cli", "s2-build", "--config", C["config"],
             "--zones-only", "--zone", z, "--years", C["years"],
             "--out-dir", os.path.join(WORK, "s2")],
            cwd=SRC, env=e, stdout=log, stderr=subprocess.STDOUT), log))
    for z, p, log in procs:
        rc = p.wait()
        log.close()
        print(f"zone {z}: rc={rc}", flush=True)
        print(open(os.path.join(WORK, f"log_{z}.txt")).read()[-3000:], flush=True)
    n = len(glob.glob(os.path.join(WORK, "s2", "*", "*.tif")))
    print(f"done: {n} tiles in {time.time() - T0:.0f}s  run_id={C['run_id']} commit={C['commit']}")


if __name__ == "__main__":
    main()
