# PROGRESS — RoadWatch AP

> Living log. Read this and `DECISIONS.md` at the start of every session.
> Newest status block on top.

## Current status (2026-10-14, end of Day 1 work block 1)

- **Phase:** CP1 sprint, Day 1 of 6 (ADR-006). **CP1 review ≈ Tue 2026-10-20.**
- **Done today:** foundation (repo, env, configs, AOI, frozen holdout, checks, CI files, tests 17/17).
- **Blockers:** Kaggle + Hugging Face accounts (needed before Day 2 training). DINOv3 licence approval (request now; approval can take time).

## CP1 6-day plan (ADR-006)

| Day | Date | Work | Gate / evidence |
|---|---|---|---|
| 1 | Wed 14 Oct | Repo, env, configs, AOI + zones, frozen holdout, check scripts, CI · accounts: Kaggle, HF (+ DINOv3 licence), GitHub | `roadwatch info`, tests green, **Gate 1** draft |
| 2 | Thu 15 Oct | Data pipeline: STAC search (Planetary Computer), windowed reads, seasonal composites, cloud mask, CRS/registration checks, tile registry + reserve log · OSM road labels → masks · Kaggle notebook **Baseline A** (U-Net/D-LinkNet ResNet34, DeepGlobe) **1-epoch timing run** | unit tests on fixtures, timing → GPU-hour estimate |
| 3 | Fri 16 Oct | Baseline A full run (teammate run cards) · Reference B: DINOv3 frozen + head (if licence approved) · Sentinel-2 road model on AP chips | RUN_LOG rows, checkpoints on HF |
| 4 | Sat 17 Oct | Inference on zones A/B/C · mask → skeleton → graph → GeoJSON/GPKG/Shapefile · minimal FastAPI + MapLibre page | map showing extracted roads |
| 5 | Sun 18 Oct | KPI-1 table (IoU/F1 + APLS-on-skeleton) with 95% bootstrap CIs, per condition (occlusion/terrain/zone) · failure log · resource profile · NT stubs | `reports/kpi1_cp1.md` |
| 6 | Mon 19 Oct | `reports/CP1_report.md`, slide outline, demo script, 2-min video plan, **Gate 2** checklist, rehearsal | review pack |

## Team (ADR-009)
| Person | Role | Runs Kaggle jobs |
|---|---|---|
| You | Model engineering lead | yes |
| A | Spatial evidence & provenance lead | yes |
| B | GIS workflow & delivery lead | yes |
| C | Validation & uncertainty lead | yes |
| D | Training-runs & reproducibility lead | yes |

## Done

### 2026-10-14 — Day 1, block 1: foundation
- `pyproject.toml` + uv env on Python 3.11.16 (`.python-version`), uv cache inside project.
- `src/roadwatch/config.py`: Pydantic configs; all lean rules are switches (`configs/lean.yaml`); config hash.
- AOI boundaries from OSM (`scripts/fetch_boundaries.py`): AP 163,136 km² · NTR 3,285 · Krishna 3,826.
- Zones A/B/C (`configs/zones.yaml`), pilot AOI = NTR ∪ Krishna ∪ zones = 7,152 km², 374 tiles.
- Deterministic tile grid (`data/grid.py`) and frozen spatial holdout (`data/splits.py`, `evidence/holdout/`): 95/489 AP blocks test + 3 zones; sha256 8a9150a57d46.
- CLI: `uv run roadwatch info`, `roadwatch holdout freeze|check`.
- `scripts/check_env.py`, `scripts/disk_check.py` (project 1.18 GB / 3 GB limit; drive 267 GB free).
- `.env.example`, `.github/workflows/ci.yml`, `LICENSES_DATA.md`, `evidence/manifest.csv`, `README.md`.
- Tests: 17 passed, ruff clean.

Evidence (`uv run roadwatch info`):
```
aoi   : ntr_krishna_pilot  area=7,152 km2
grid  : 512px @ 10.0 m, crs=auto_utm  tiles=374  epsg=[32644]
splits: train 177, zone_test 70, buffer 50, test 46, val 31
```

### 2026-10-14 — Section 0.1 kick-off
- Machine check: Win 11 Home, PS 5.1, i9-13900HX, 15.7 GB RAM, RTX 4070 Laptop 8 GB, E: 250 GB free, uv 0.12.5, Git 2.55, Node 24.
- Section 13 batch-1 answers: teammates A–D; review in 6 days; all three zones; accounts on demand; public repo; disk option B.

## Next
1. 🔴 Kaggle account + API token, Hugging Face account + token + DINOv3 licence request, GitHub repo push.
2. Day 2: data pipeline + Baseline A Kaggle notebook (timing run).

## Blockers / waiting on user
- Kaggle (phone-verified) + API token in `.env`.
- Hugging Face token in `.env` + DINOv3 licence request + org name.
- GitHub: create public repo, then I push.
