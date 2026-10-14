# DECISIONS — Architecture Decision Records

> One ADR per decision. Status: Proposed / Accepted / Superseded by ADR-xxx.
> Cheap-to-redo choices are made by the engineer and logged here; expensive ones wait for the user.

---

## ADR-001 — Repository root is `E:\cap-22`
- **Status:** Accepted (2026-10-14)
- **Context:** Section 5 shows a `roadwatch/` root folder. The project folder already exists at `E:\cap-22` with `PROJECT_PROMPT.md` in it.
- **Decision:** `E:\cap-22` *is* the `roadwatch/` repo root. Python package lives at `src/roadwatch/`.
- **Consequence:** No extra nesting level; all paths in docs are relative to `E:\cap-22`.

## ADR-002 — Python 3.11 via uv
- **Status:** Accepted (2026-10-14)
- **Context:** Section 4 fixes Python 3.11. Machine has 3.13 / 3.12 / 3.10, not 3.11. Kaggle images and geo wheels (rasterio, GDAL, geopandas) are best supported on 3.11.
- **Decision:** `uv python install 3.11`, pin with `.python-version`. Keep uv cache inside the project (`UV_CACHE_DIR=.cache/uv`, git-ignored) per Section 2.
- **Consequence:** Same minor version locally and on Kaggle → fewer "works on Kaggle, not locally" bugs.

## ADR-003 — Disk budget: prompt says 2–4 GB free, machine has much more
- **Status:** Accepted — option B (user, 2026-10-14). Enforced by `scripts/disk_check.py`.
- **Context:** Section 2 assumes only 2–4 GB free. Measured: E: (project drive) 249.9 GB free, D: 209.7 GB, C: 19.2 GB. Also a local RTX 4070 (8 GB VRAM) exists, while Section 2/4 say "no CUDA PyTorch locally".
- **Options:**
  - A. Keep the strict 3 GB cap and CPU-only ONNX locally (as written).
  - B. Keep the project under 3 GB in Git/env, but allow a git-ignored `data_cache/` on E: (cap 30 GB) for pilot-zone chips and fast local debugging; still no training locally.
- **Recommended default:** B (faster iteration, still all training on Kaggle, all lean rules unchanged).

## ADR-004 — Scripts target Windows PowerShell 5.1
- **Status:** Accepted (2026-10-14)
- **Context:** Only Windows PowerShell 5.1 is installed (no `pwsh` 7).
- **Decision:** All documented commands must run in PowerShell 5.1 (no `&&`, no `??`). Python CLIs (`uv run roadwatch ...`) do the real work so shell differences don't matter.

## ADR-005 — Provisional defaults for Section 13 questions not yet asked
- **Status:** Proposed (2026-10-14) — will be confirmed in question batch 2 (dates, KL template, paper)
- **Decision (provisional):** Monitoring dates 2022–2026, 2 per year (pre-monsoon Mar–May, post-monsoon Oct–Dec) · KL University report/slide templates unknown → generic IEEE-style report until a template arrives · research paper target: yes, draft in CP2.
- **Consequence:** Week 1 work isn't blocked; all three are config/doc changes, cheap to redo.

## ADR-006 — CP1 compressed from 4 weeks to 6 days
- **Status:** Accepted (2026-10-14). User: "review in 6 days" → CP1 review ≈ 2026-10-20.
- **Decision:** Keep the CP1 *vertical slice* (data pipeline → Baseline A → masks → graph → GeoJSON → map page → KPI-1 table with CIs). Cut/defer:
  - SAM-Road → CP2.
  - Reference B (DINOv3) only if the gated licence is approved by Day 3; otherwise it stays planned, and Baseline A vs a second CNN encoder is the O2 comparison for CP1.
  - Supabase, Telegram, Gemini, Earth Engine, Copernicus, Bhoonidhi accounts → CP2.
  - Docs written as short versions; completed in CP2.
- **Consequence:** The CP1 report must state these cuts plainly. Nothing is deleted, only postponed.

## ADR-007 — Spatial holdout on one India-wide grid (EPSG:7755), frozen 2026-10-14
- **Status:** Accepted
- **Decision:** 20.48 km square blocks (4×4 Sentinel-2 tiles) on EPSG:7755 (WGS 84 / India NSF LCC). A block's split comes from sha256(seed, bx, by): 20% test, 10% val, rest train. Any chip within 1 km of a test block is `buffer` (never trained or tuned on). Tiles use per-UTM-zone grids with IDs `T{epsg}_{res}m_{size}_{col}_{row}`.
- **Why:** The split must not depend on the AOI, so pilot, statewide and any later India run see the same test set. Hash-based means no stored random state can be lost.
- **Evidence:** `evidence/holdout/` — 95 / 489 AP blocks are test; sha256 `8a9150a57d46…`. CI and `tests/test_splits.py` fail if it changes. `roadwatch holdout freeze` refuses to overwrite.

## ADR-008 — All three high-res zones are evaluation-only holdout
- **Status:** Accepted (user chose all three zones, 2026-10-14)
- **Decision:** Zones A (Vijayawada W. bypass), B (Machilipatnam port), C (Gannavaram–Nunna) are `zone_test`: never trained or tuned on, with a 1 km buffer. Pilot AOI = NTR ∪ Krishna ∪ zone boxes (zone A crosses into Guntur district).
- **Why:** New-road detection (KPI-2/3) and the demo are measured in these zones, so training on them would inflate results.
- **Cost:** 70 of 374 pilot tiles are not trainable; this is irrelevant statewide (~6,200 tiles).

## ADR-009 — Team roles
- **Status:** Accepted (provisional names A, B, C, D — replace with real names any time)
- **Decision:** User = Model engineering lead (codes). A = Spatial evidence & provenance lead. B = GIS workflow & delivery lead. C = Validation & uncertainty lead. D = Training-runs & reproducibility lead. All four run Kaggle jobs on their own accounts; seeds are split across accounts.

## ADR-010 — Public GitHub repository
- **Status:** Accepted (user, 2026-10-14)
- **Consequences:** No secrets (`.env` git-ignored, `check_env.py` prints only PRESENT/MISSING). No imagery, model weights or ISRO data in Git (`.gitignore` blocks *.tif, *.pt, *.onnx, data_cache/). Only small OSM-derived GeoJSON (ODbL, attributed).

## ADR-011 — Boundaries via Nominatim lookup, not Overpass
- **Status:** Accepted (2026-10-14)
- **Context:** Overpass mirrors returned 406/504 errors during setup. Nominatim `lookup?osm_ids=R…&polygon_geojson=1` returns the same OSM relation polygons.
- **Decision:** `scripts/fetch_boundaries.py` uses fixed relation IDs through Nominatim (≤1 req/s). Areas check out: AP 163,136 km², NTR 3,285 km², Krishna 3,826 km².