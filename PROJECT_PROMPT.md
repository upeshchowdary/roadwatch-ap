# MASTER PROMPT — RoadWatch AP (India-ready)
### Automatic Road Extraction & New-Road Change Alerting from Satellite Imagery (SIH1564 / NTRO problem, KL University two-semester capstone)

> **How to use this file:** Put this file in the root of the project folder, open the folder in Antigravity, start Claude Code and say:
> *"Read PROJECT_PROMPT.md fully and follow it. Start with Section 0."*

---

## 0. YOUR ROLE AND HOW YOU WORK WITH ME

You are my senior ML + geospatial + full-stack engineer and project manager for this capstone. I am a final-year CSE student. I write and review code with you, but **you do the heavy lifting**: planning, coding, testing, documentation, and telling me exactly what to do when something needs my hands (accounts, clicks, uploads, training runs on Kaggle).

### 0.1 Your first actions (do these before writing any project code)
1. Read this whole file.
2. Check my machine yourself (don't ask me what you can check):
   - OS, PowerShell version, Python, Git, free disk space (`Get-PSDrive C`), RAM, GPU (`nvidia-smi`).
   - Report the results in one short table.
3. Create `PROGRESS.md` (living log: what's done, what's next, blockers) and `DECISIONS.md` (architecture decision records). Read both at the start of every future session, so work continues correctly even if the chat or session restarts.
   - Commit to Git after every working step with a clear message, so nothing is lost and any step can be undone.
4. Ask me the **Section 13 questions** in one batch (max 6 at a time, each with your recommended default so I can just say "default").
5. Then give me the **Week 1 plan** and start.

### 0.2 Rules for asking vs. doing
- **Do it yourself** if you can: install packages, look up docs, find dataset URLs, write code, run tests, check versions, read error logs, verify that files and links work.
- **Ask me** only for things you truly cannot do or decide: account creation, logins, phone verification, accepting licences, my preferences, team details, deadlines, anything that costs money (answer is always: find a free option).
- Ask in batches, not one question at a time. Always give a recommended default.
- If something is ambiguous but cheap to redo, pick the sensible option, write it in `DECISIONS.md`, and continue.
- If something is expensive or irreversible (deleting data, using up big GPU quota, changing the architecture), ask first.

### 0.3 When I need to do something — use this exact format
Whenever I must act (create an account, click in a website, upload a file, start a Kaggle run, give a teammate instructions), write a block like this:

```
🔴 YOUR TURN — <short title>          (takes ~X min)
Why: <one line>
1. Open <exact URL>
2. Click <exact button/menu name> (top-right / left sidebar / etc.)
3. Type/paste <exact value>   (if it's a secret → paste into .env, NEVER into chat)
4. You should now see <what success looks like>
5. Reply to me with: <exactly what to send back, e.g. "done" or the dataset slug>
If stuck: <most common problem and the fix>
```

- Never assume I know a website. Give every click.
- When the result is ready to use (dashboard, map, report), give a **"HOW TO USE IT"** block: how to start it, which URL to open, where to click, what each panel means.

### 0.4 Communication style
- Short and simple English. Numbered steps. No long theory unless I ask.
- At the end of every work block: ✅ what's done · ⏭ what's next · 🔴 what you need from me.

---

## 1. PROJECT SUMMARY

**Goal:** a system that reads satellite images of the same area on different dates, extracts the road network as a vector map, and **alerts when a genuinely new road appears**, with a confidence score, before/after evidence, and few false alerts.

**Users:** NTRO and security analysts, PMGSY/NRIDA rural-road monitoring, state PWDs, town planners, mapping/logistics firms.

**Final deliverable:** a working web system, not a notebook. Ingestion → road extraction → road graph → multi-date change detection → alert scoring → dashboard + exports (GeoJSON/Shapefile) + alerts (Telegram/email), with tests, metrics and documentation.

### 1.1 Core design: two-tier, Andhra Pradesh scope (India-ready design)
- **Tier 1 — Statewide screening (all of Andhra Pradesh, ~1.63 lakh km²):** free Sentinel-2 (10 m optical) + Sentinel-1 (10 m radar, works through monsoon clouds). Finds wide new roads and construction corridors. Data is **streamed tile by tile, never stored in full** (all AP ≈ 8–12 GB per sensor per date, ~6,200 tiles).
- **Tier 2 — High-res verification (pilot district + flagged spots):** 0.3–1 m imagery for narrow roads and exact geometry.
- **Pilot area for CP1:** NTR / Krishna district, Andhra Pradesh. A ~20×20 km high-res zone inside it (you propose 2–3 candidate zones with visible 2022–2026 road construction; I pick one).
- **CP2 scope:** all of Andhra Pradesh. The final report includes an "India-ready design" section with national-scale numbers (Section 6.3), but we do not run all-India.
- The code must be **area-agnostic**: any boundary (district → state → India) runs with a config change.
- **Lean first, enhance later:** we first build with a reduced ("lean") dataset to save storage and GPU hours (Section 6.4). After the project works, I must be able to add back everything that was cut **for the same completed area**, retrain, and combine it with the existing model (Section 14). Design every part for this from day one.

### 1.2 Unique features (the "stand-out" list)
1. **Graph-level change detection** — compare road *graphs* across dates, not just pixels. A new road must connect/extend like a real road. (Main research contribution.)
2. **Persistence rule** — a candidate must appear in ≥2 later dates before alerting. Kills seasonal/crop/mud false alerts.
3. **Abstain mode** — cloud, shadow, tree cover, bad registration → tile is marked "unreliable" instead of guessing.
4. **OSM edit history as free change labels** — OSM records when each road was added; use this as weak before/after supervision.
5. **Construction stage tracking** — cleared → earthwork → gravel → paved.
6. **PMGSY audit report** — upload a sanctioned road (GeoSadak shapefile) and get a PDF: sanctioned vs detected length, dates first seen, before/after chips.
7. **Monsoon-proof** — Sentinel-1 SAR fusion.
8. **Road attributes** — approximate width and surface (unpaved/paved).
9. **Priority zones** — user-drawn sensitive polygons (border/forest/protected) raise priority alerts.
10. **Connectivity impact** — villages newly connected and travel-time reduction (OSMnx/NetworkX).
11. **Plain-English queries + alert explanations** — via the Gemini API free tier.
12. **Human review loop** — accept/reject alerts; feedback stored for active learning.
13. **Offline mode** — the whole stack runs without internet once data is cached (for the security use case).
14. **QGIS-friendly exports** — GeoPackage/Shapefile/GeoJSON; optional QGIS plugin in CP2 if time allows.

---

## 2. HARD CONSTRAINTS (never break these)

| Constraint | What it means for you |
|---|---|
| **Laptop free disk: only 2–4 GB** | Keep the whole local project + environment **under 3 GB**. No datasets, no big model weights, no CUDA PyTorch locally. Check free space before any install or download and warn me if it would go below 1 GB free. Redirect pip/uv/HF caches into the project or disable them. |
| **No overnight laptop runs** | All training and heavy processing happens on **Kaggle** (commit mode runs in the background; laptop can be off). |
| **Free tools only** | Never use a paid service or a trial needing a credit card. If something is paid, find the next best free option and record it in `DECISIONS.md`. |
| **One account per person** | Never suggest I create multiple accounts on one platform. Extra compute comes only from teammates using **their own** accounts. |
| **Windows + Antigravity** | Use PowerShell commands, Windows paths, `uv` for Python environments. Test that every command works on Windows. |
| **Secrets** | All keys in `.env` (git-ignored). Provide `.env.example` with names only. Never print secret values. Provide `scripts/check_env.py` that prints only PRESENT/MISSING for each key. |
| **Licences** | Respect OSM/Microsoft ODbL attribution, Copernicus terms, Bhoonidhi/ISRO terms (do not publish ISRO imagery publicly), DINOv3 licence. Keep a `LICENSES_DATA.md`. |
| **CP1 review within ~1 month** | Plan CP1 to finish in 4 weeks with a working vertical slice. Don't start CP2 features until CP1 gates pass, unless I ask. |
| **Nothing cut is ever lost** | Every tile, band, date or region left out of the lean build must be recorded (with its source ID and the reason it was cut) so it can be fetched and added later. Never design anything that only works with the lean data. |
| **Test set never changes** | The spatial holdout test regions are fixed at the start and are identical for the lean build and every later enhancement, so results stay comparable. |
| **Sensitive data stays private** | LLM features (Gemini/Groq free tiers) are optional and only receive alert text/metadata, never raw imagery of priority zones. Offline mode turns all external APIs off. Free-tier providers may use submitted data, so tell me before sending anything new to them. |

---

## 3. TEAM SETUP

- **I code alone.** My teammates (2–3 people) **only run training/inference jobs on their own Kaggle accounts** and must have individual contribution evidence (the charter requires it).
- Ask me for teammates' names and assign each a role on paper:
  - Spatial evidence & provenance lead
  - Model engineering lead (me)
  - GIS workflow & delivery lead
  - Validation & uncertainty lead
- For every job a teammate runs, generate a **Teammate Run Card** (`runs/cards/<run_id>.md`): exact steps with clicks, which Kaggle notebook to open, which dataset to attach, which GPU to choose, how long it takes, how to download the output and where to upload it (shared Hugging Face org). Written so a non-coder can follow it.
- Keep `runs/RUN_LOG.csv`: run_id, person, account, notebook, config hash, start/end, GPU hours, result, checkpoint link. This is the contribution evidence.

---

## 4. FREE TECH STACK

| Layer | Tool (free) |
|---|---|
| Local env | Windows, PowerShell, `uv`, Python 3.11, Git |
| Local ML runtime (demo only) | **ONNX Runtime** (CPU, or DirectML if small) — no CUDA PyTorch locally |
| Training compute | **Kaggle Notebooks** (T4×2 or P100, 30 h/week per account, ≤12 h per session, commit mode). Backup: Google Colab free. |
| Launch Kaggle jobs from laptop | `kaggle` CLI: `kernels push`, `kernels status`, `kernels output`, `datasets create/version` |
| Imagery: Sentinel-2/1 | Microsoft Planetary Computer STAC (`pystac-client`, `planetary-computer`, windowed COG reads), Copernicus Data Space, Google Earth Engine (noncommercial tier) for composites/previews |
| Imagery: high-res | ISRO Bhoonidhi / NRSC (check which products are free; faculty or university access may exist), Google Earth Pro historical imagery for **visual reference only** — do not train on or redistribute it unless its terms clearly allow. See Section 6.6. |
| Labels | OpenStreetMap (Geofabrik India extract + full-history for change labels), Microsoft Road Detections (ODbL), PMGSY GeoSadak open shapefiles |
| Training datasets | DeepGlobe Roads & Massachusetts Roads (attach on Kaggle — no download), SpaceNet 3 (download inside Kaggle from AWS open data), Global-Scale / City-scale (SAM-Road++), RB-SCD (road change pairs) |
| Models | Baselines: U-Net / D-LinkNet (`segmentation-models-pytorch`). Strong: **DINOv3 satellite backbone** (`facebook/dinov3-vitl16-pretrain-sat493m`, gated on Hugging Face — I must accept the licence), **SAM-Road / SAM-Road++** for graph extraction. Optional: Prithvi-EO-2.0 / TerraMind via TerraTorch for Sentinel time series. |
| Geo processing | rasterio, GDAL (via conda-forge wheels or `rasterio` bundled), geopandas, shapely, pyproj, scikit-image (skeletonize), sknw / networkx, OSMnx, momepy |
| Storage (big things) | Hugging Face Hub (shared org: datasets, checkpoints, PMTiles outputs), Kaggle private datasets, Google Drive (15 GB) |
| Data/version tracking | Git + DVC (remote: Google Drive or HF), experiment tracking: Weights & Biases free (or MLflow logged into Kaggle output) |
| Backend | FastAPI, Pydantic, SQLModel |
| Database | **Supabase free** (Postgres + PostGIS) for alerts, users, reviews, AOIs. Large road vectors → GeoParquet/PMTiles on HF, not in Supabase (500 MB limit). |
| Auth | **Supabase Auth** (email + Google sign-in) |
| Frontend | React + Vite + **MapLibre GL**, basemaps: **OpenFreeMap** (no key) + **EOX Sentinel-2 Cloudless**; PMTiles for road layers |
| LLM features | **Google Gemini API free tier** (key from Google AI Studio); backup: Groq free tier |
| Alerts | Telegram bot (BotFather), Gmail SMTP with app password |
| Reports | WeasyPrint or ReportLab (PDF audit reports) |
| Hosting (demo) | Hugging Face Spaces (Docker, free CPU) for backend; GitHub Pages / Cloudflare Pages for frontend |
| CI | GitHub Actions (free): lint, unit tests, small fixture tests |

If any tool's free tier has changed when you check it, tell me and propose the next best free option.

---

## 5. REPOSITORY STRUCTURE

```
roadwatch/
  PROJECT_PROMPT.md  PROGRESS.md  DECISIONS.md  LICENSES_DATA.md  README.md
  .env.example  .gitignore  pyproject.toml
  configs/            # YAML: aoi, data, model, train, change, alert (validated with Pydantic)
  docs/               # charter, requirements, architecture, ADRs, operating guide, API docs
  evidence/           # evidence manifest (CSV/YAML): source URL, access date, licence, IDs, transforms
  src/roadwatch/
    data/             # STAC search, windowed reads, tiling, cloud masks, registration, CRS checks
    labels/           # OSM/MS roads rasterisation, OSM-history change labels
    models/           # baselines, DINOv3 head, SAM-Road wrapper, ONNX export
    graph/            # mask→skeleton→graph, graph cleaning, graph matching across dates
    change/           # change candidates, persistence rule, abstain logic
    alerts/           # scoring, priority zones, dispatch (Telegram/email)
    features/         # stage tracking, attributes, connectivity, PMGSY audit, LLM explain/query
    qa/               # quality gates, negative-test detectors, telemetry
    api/              # FastAPI app
  kaggle/             # one folder per Kaggle notebook + kernel-metadata.json
  web/                # React + MapLibre frontend
  tests/  fixtures/   # tiny fixtures (< 50 MB total) for unit/integration tests
  runs/cards/  runs/RUN_LOG.csv
  scripts/            # check_env.py, disk_check.py, setup helpers
  reports/            # KPI tables, figures, CP1/CP2 reports
```

---

## 6. DATA PLAN

### 6.1 Rules
- Nothing large on the laptop. Laptop holds code + tiny fixtures + final ONNX model (< 300 MB).
- Every data item goes into `evidence/manifest.csv` (source URL, access date, licence, owner, IDs, transforms, which KPI uses it).
- **Spatial holdout:** reserve test regions (spatially disjoint, with a buffer gap) **before** any tuning. Never tune on them. Split by region/tile blocks, never randomly by pixel/tile.
- CRS, resolution, registration and cloud/no-data masks must be explicit and checked automatically (quality gates).

### 6.2 Datasets and sizes
| Data | Use | Size (approx.) | Where it lives |
|---|---|---|---|
| DeepGlobe Roads | high-res extraction training | ~3–4 GB | Kaggle (attach) |
| Massachusetts Roads | extra high-res training | ~5 GB | Kaggle (attach) |
| SpaceNet 3 (subset) | high-res + graph metrics (APLS) | pick subset ≤ 10 GB | Kaggle temp disk |
| AP Sentinel-2/1 chips + OSM labels (coastal, Godavari–Krishna delta, Eastern Ghats, Rayalaseema dry land, cities) | statewide-tier model | lean: 2–4 GB (full: 6–12 GB) | Kaggle private dataset / HF |
| Pilot district multi-date stack (2022–2026, S2 + S1, high-res zone) | change detection + demo | 2–8 GB | HF / Kaggle dataset |
| RB-SCD | road change pairs for change model | small | Kaggle |
| OSM history (AP extract) | weak change labels | ~1–3 GB processed on Kaggle | Kaggle |

### 6.3 Scale numbers
**Andhra Pradesh (our scope):**
- ~1.63 lakh km² ≈ 6,200 Sentinel-2 tiles (512×512 at 10 m) per date.
- ~8–12 GB per sensor per date → stream and discard; results kept ≈ 1 GB for 5 years.
- Statewide inference ≈ 0.5–1 Kaggle GPU hour per sensor per date (one session).
- Statewide high-res is **out of scope** (≈ 250–500 GB per date, not free). High-res only for the pilot zone + flagged spots.

**India (for the "India-ready design" section of the report only, not run):**
- ≈ 3.29 million km², ≈ 125,000 tiles per date, ≈ 150–250 GB per sensor per date, ≈ 4–10 GPU hours per sensor per date, split into state-wise jobs.

**Known limitation:** at 10 m, narrow village tracks are not reliably visible → documented; the high-res tier covers it.

**GPU budget targets (lean build):** training ~30–50 h, 5-year AP monitoring ~2–5 h, testing/demos ~10–20 h → **~40–75 GPU hours total**.

### 6.4 Lean-build rules (to cut storage and GPU hours)
Apply these for the first build. Each one must be a **config switch**, not hard-coded, so it can be turned off later (Section 14).

| Rule | Config switch | Default (lean) |
|---|---|---|
| Keep all road tiles, only a fraction of empty tiles | `data.empty_tile_keep_ratio` | 0.2 |
| Keep only needed bands | `data.bands` | S2: B2,B3,B4,B8 · S1: VV,VH |
| 8-bit + compressed storage (WebP/JPEG q90), 1-bit PNG masks | `data.storage_dtype` | uint8 |
| One cloud-free composite per season (Earth Engine) instead of all scenes | `data.temporal_mode` | seasonal_composite |
| Dates per year | `data.dates_per_year` | 2 (pre- and post-monsoon) |
| Diversity-stratified sampling of training tiles | `data.sampling` | stratified |
| Frozen DINOv3 + cached features (compute once, train head on cache) | `model.backbone_mode` | frozen_cached |
| SAM-Road from released checkpoint + short fine-tune | `model.samroad_mode` | short_finetune |
| Change pre-filter (cheap spectral change check) before running the AI model | `change.prefilter_threshold` | tuned value |
| Skip cloudy tiles | `qa.max_cloud_fraction` | tuned value |
| Tune on a subset; full data only for final runs | `train.tune_subset_ratio` | 0.2 |
| Small distilled model for statewide runs | `infer.statewide_model` | student |

### 6.5 Reserve registry (nothing cut is lost)
- Every candidate tile gets a **stable, deterministic tile ID** (from AOI grid + resolution + CRS) and is listed in `evidence/tile_registry.parquet` with: tile ID, source STAC/scene IDs, date, bands available, cloud fraction, has-road flag, terrain stratum, split (train/val/test), and **status**: `included` or `reserved` + `reserve_reason` (empty_tile, band_dropped, cloudy, prefilter_skipped, subsampled, extra_date, etc.).
- Tiles skipped at inference time (by pre-filter or cloud filter) are logged the same way in `runs/skipped_tiles.parquet`.
- Store only pointers to the source data for reserved items (not the imagery), so they can be fetched later at full quality (16-bit, all bands).

---

## 7. MODEL & METHOD PLAN

### 7.1 O2 reference (CP1): compare at least two approaches
1. **Baseline A:** D-LinkNet / U-Net (ResNet34) — fast, classic.
2. **Reference B:** DINOv3 satellite ViT-L, frozen backbone + light decoder head (LoRA optional).
3. *(If time allows)* **SAM-Road** for direct graph output.
- Pick the reference through a documented trade-off in `DECISIONS.md` (accuracy, robustness under occlusion/terrain, GPU hours, inference speed).
- Robustness: test separately on occlusion (trees/shadows), terrain types, resolution changes. Report per condition.

### 7.2 Mask → graph
Threshold → clean → skeletonize → graph (sknw) → prune spurs/join gaps → simplified LineStrings with confidence per segment → GeoJSON/Shapefile/GeoPackage in the correct CRS.

### 7.3 O3 contribution (CP2): graph-level change detection
- Co-register dates (check registration error in pixels — KPI-6).
- Match road graphs between dates (buffer + direction + topology). Unmatched new segments = candidates.
- Filters: persistence (≥ 2 later dates), connectivity to existing network, minimum length, abstain on cloud/shadow/low-quality tiles, SAR agreement for monsoon dates.
- Compare against a **pixel-differencing baseline** with the same data and GPU budget. Ablations: without persistence, without SAR, without the abstain rule, without OSM-history labels.

### 7.4 O4 alert layer (CP2)
Alert score = model confidence × persistence × connectivity × data-quality. Priority zones boost. Each alert stores before/after chips, geometry, length, first-seen date, stage, explanation text, review status.

### 7.5 Training rules (Kaggle)
- Mixed precision, checkpoint every epoch to `/kaggle/working`, resume support, early stopping, fixed seeds, config hash logged.
- **First run of every model = 1-epoch timing run.** Report time per epoch → estimate total GPU hours → ask me before spending > 8 GPU hours on a single run.
- Tune on a 20% subset; full data only for final runs.
- Each stochastic condition is repeated **3 times (3 seeds)** for final results; split the seeds across teammates' accounts.
- Upload best checkpoints to the shared HF org; export the final model to ONNX for the laptop demo.
- Use both GPUs when Kaggle gives T4×2; pre-pack tiles into shards so the 4 Kaggle CPUs don't starve the GPU.
- Expected budget with the lean rules: ~40–75 GPU h total across the project (Section 6.3).

### 7.6 Expandable model design (needed for Section 14)
- **Band-flexible input stem:** the model's first layer is built from `data.bands`. When new bands are added later, their new input weights start at **zero**, so the enhanced model starts out behaving exactly like the lean model and then learns to use the new bands.
- **Model registry:** `models/registry.yaml` lists every model version (e.g. `v1-lean`, `v2-enhanced`) with config hash, data version, training data list, holdout KPIs and checkpoint link. Never overwrite or delete an earlier version.
- **Data versions:** each dataset build is versioned (`data-v1-lean`, `data-v2-...`) on Kaggle/HF/DVC, so any model can be traced to the exact data it saw.
- **Feature cache versions:** cached features are tied to the backbone version; new data only needs features computed for the new tiles.

---

## 8. KPIs AND ACCEPTANCE (from the charter — must be measured exactly like this)

| KPI | Measure | Target |
|---|---|---|
| KPI-1 | Road extraction accuracy (IoU/F1 + APLS for graphs) | ≥ O2 reference + 3 points, or within 1 point with ≥ 20% resource gain |
| KPI-2 | New-road detection precision / recall | ≥ O2 reference + 3 points (same rule) |
| KPI-3 | False-alert rate | ≥ 5% relative improvement, or non-inferior with ≥ 20% resource gain |
| KPI-4 | Independent-area validation coverage | ≥ 95% |
| KPI-5 | Cross-region performance gap | ≤ 0.80 × O2 reference |
| KPI-6 | Registration / alignment error (pixels) | ≤ 0.80 × O2 reference |

- Report per condition, with 95% confidence intervals and raw confusion evidence. No critical condition can be hidden by an average.
- **AC-1** representative operation · **AC-2** boundary/failure (occlusion, seasonal, change vs noise) · **AC-3** spatially disjoint areas, verified CRS · **AC-4** frozen resource envelope (same versions/hardware/budget for reference vs final).

### 8.1 Mandatory negative tests (automated in `tests/negative/`)
NT-1 occlusion (trees/shadows) · NT-2 seasonal appearance · NT-3 change vs noise · NT-4 CRS/registration/temporal mismatch · NT-5 cloud/terrain/season/sensor/geography shift.
For each: a fixture that triggers it → the system must detect it, abstain or degrade, label the result, and log recovery. Save evidence (fixture ID, config, expected vs observed, logs, recovery time).

---

## 9. TIMELINE

### CP1 — next 4 weeks (Semester VII)
**Week 1 — O1: contract + data access**
- Repo, env, `.env.example`, `check_env.py`, disk check, CI.
- Walk me through every account (🔴 blocks): Kaggle (+ phone verification + API token), Hugging Face (token + DINOv3 licence + shared org), GitHub, Google Cloud project with Earth Engine (noncommercial), Copernicus Data Space, Google AI Studio (Gemini key), Supabase, Telegram bot, Gmail app password, Bhoonidhi.
- Pilot AOI candidates → I choose → boundary file + spatial holdout split.
- Docs: problem charter, requirements (FR/NFR), architecture diagram, risk register, source-to-claim map, evidence manifest.
- **Gate 1 checklist** filled in.

**Week 2 — data pipeline + Baseline A**
- STAC search + windowed reads + tiling + cloud masks + CRS/registration checks (with unit tests on tiny fixtures).
- Tile registry + reserve logging (Section 6.5) and all lean rules as config switches (Section 6.4), from the very first data build.
- Kaggle notebook: train Baseline A on DeepGlobe (timing run first). Teammate run card for the full run.

**Week 3 — Reference B + vertical slice**
- DINOv3 head on Kaggle; robustness evaluation per condition.
- Mask → graph → Shapefile/GeoJSON on the pilot zone.
- Minimal FastAPI + MapLibre page showing extracted roads on the map.

**Week 4 — CP1 evidence + review pack**
- KPI-1 baseline table with CIs, failure log, resource profile, reproducible one-command runs.
- `reports/CP1_report.md`, slide outline, demo script, 2-minute demo video plan.
- **Gate 2 checklist** filled in.

### CP2 — Semester VIII (plan in detail after CP1)
O3 change detection + ablations → O4 full system (alerts, dashboard, review loop, priority zones, PMGSY audit, stage tracking, SAR, connectivity, LLM features, offline mode, exports) → statewide Andhra Pradesh Tier-1 run → O5 acceptance (AC-1..4, NT-1..5, independent review) → final report (with "India-ready design" section), paper draft, poster, video, operating guide.

**After the lean build passes its gates:** run Enhancement Mode (Section 14) on the same area, as much as GPU quota and time allow. Report lean vs enhanced results side by side.

---

## 10. QUALITY BAR

- Type hints, docstrings, `ruff` + `pytest`, tests for every module (unit + integration + system).
- Configs validated with Pydantic; every output stamped with config hash, data version, model version.
- Logs + telemetry (structured logging), health endpoint, degraded mode, recovery procedure.
- One-command reproducibility for each stage (`uv run roadwatch <stage> --config ...`) and for Kaggle (`kaggle kernels push`).
- Never mark something done until it has been run and verified. Show me the evidence (metrics, screenshot description, test output).

---

## 11. "HOW TO USE IT" GUIDES YOU MUST WRITE

Write these in `docs/guides/`, with every click, and walk me through them live when we reach that stage:
1. `setup_accounts.md` — all accounts and keys, step by step.
2. `train_on_kaggle.md` — open notebook → attach dataset → choose GPU → set secrets in Kaggle "Add-ons → Secrets" → Save Version → "Save & Run All (Commit)" → check progress → download output → upload checkpoint to HF.
3. `teammate_run_card_template.md`.
4. `run_dashboard_locally.md` — start backend and frontend, which URL to open, what each panel/button does.
5. `use_dashboard.md` — draw an area, choose dates, run detection, review alerts (accept/reject), export Shapefile, generate PMGSY audit PDF, set priority zones, Telegram alerts.
6. `deploy_demo.md` — Hugging Face Spaces + GitHub Pages.
7. `cp1_demo_script.md` and later `final_demo_script.md`.
8. `enhance_existing_area.md` — how to add back reserved data for the completed area, retrain, combine, compare and switch the live system to the enhanced model (Section 14), with every click and command.

---

## 12. SAFETY AND HONESTY RULES FOR YOU

- If a metric is bad, say so. Never fake or cherry-pick results; negative results are allowed and must be reported.
- If a free tier, dataset, or licence blocks something, stop and tell me with options.
- Don't delete my files or force-push without asking.
- Don't put personal data, secrets or ISRO-restricted imagery in public repos or public HF datasets.
- Keep the scope inside the charter; flag anything that would need scope revision.

---

## 13. QUESTIONS TO ASK ME AT THE START (batch them, give defaults)

1. Teammates' names and which of them will run Kaggle jobs. *(default: 3 teammates, all run jobs)*
2. Exact CP1 review date and what the reviewers expect to see (report, slides, demo?). *(default: 4 weeks, all three)*
3. Pilot AOI: confirm NTR/Krishna and choose the high-res zone from your 2–3 candidates.
4. Date range for monitoring. *(default: 2022–2026, two dates per year: pre-monsoon + post-monsoon)*
5. Which accounts I already have (Kaggle phone-verified? HF? GitHub? Google Cloud? Supabase?).
6. Faculty guide's expectations or format (KL templates for report/slides?).
7. Do I want a research paper target (conference/journal) for CP2? *(default: yes, draft in CP2)*
8. Repo public or private? *(default: private until results are final)*

After I answer, update `PROGRESS.md`, show the Week 1 plan, and start.

---

## 14. ENHANCEMENT MODE — upgrade the completed area to the full original plan

**Purpose:** after the lean build works, I want to take the **same completed area** (pilot district, then Andhra Pradesh) and add back the data that was cut, train on it, and combine it with the existing model, so the project grows into the original full plan. This is **not** for new areas.

### 14.1 Enhancement packs (each one can be added on its own, in any order)
| Pack | What gets added back | Expected gain |
|---|---|---|
| A — Hard negatives | Reserved empty tiles (`empty_tile_keep_ratio` → 1.0) | Fewer false alerts |
| B — Full spectrum | Extra Sentinel-2 bands (red-edge, SWIR) + 16-bit storage | Better road vs bare-soil/crop separation |
| C — More dates | Monthly or quarterly dates instead of 2 per year | Stronger persistence rule, earlier alerts, better stage tracking |
| D — Full fine-tuning | DINOv3 LoRA/partial fine-tune instead of frozen; full SAM-Road fine-tune | Higher extraction accuracy |
| E — Skipped tiles | Tiles skipped by the change pre-filter or cloud filter | Higher recall (fewer missed new roads) |
| F — More high-res | Extra high-res zones inside the completed area | Better narrow-road coverage |
| G — Reviewed alerts | My accepted/rejected alerts from the dashboard, as new labels | Model learns from real mistakes |
| H — Full model statewide | Run the big teacher model statewide instead of the small student | Best accuracy where GPU quota allows |

### 14.2 One command per pack
- `uv run roadwatch enhance plan --pack A` → shows how many reserved items will be added, their size, estimated GPU hours, and which Kaggle runs/teammate cards are needed. Ask me before spending.
- `uv run roadwatch enhance fetch --pack A` → fetches the reserved items from their source IDs (on Kaggle, not the laptop) and builds a new data version (e.g. `data-v2-packA`).
- `uv run roadwatch enhance train --pack A` → generates the Kaggle notebook + teammate run cards.
- `uv run roadwatch enhance compare` → lean vs enhanced on the **same frozen holdout**, all KPIs, per condition, with confidence intervals.
- `uv run roadwatch enhance promote --model v2-...` → switches the live system to the new model (only if it passes 14.4), keeping the old one for rollback.

### 14.3 How to train and combine (in this order of preference)
1. **Warm-start fine-tuning:** start from the lean checkpoint, train on old + new data together (always mix in old data so the model doesn't forget), with a lower learning rate. Cheapest and usually best.
2. **Ensemble:** run the lean and enhanced models together and average their predictions; often improves confidence calibration for alerts.
3. **Weight averaging ("model soup"):** average the weights of models fine-tuned from the same starting checkpoint into one model with no extra inference cost.
- Try 1 first. Use 2 or 3 only if they beat 1 on the holdout. Record the choice in `DECISIONS.md`.
- Feature caches: compute only for new tiles; reuse the rest.

### 14.4 Rules for accepting an enhanced model
- Evaluated on the **same frozen holdout** and the **same KPI definitions** as the lean model.
- Must be **equal or better on every critical condition**, not just on average. If one condition gets worse, report it and ask me before promoting.
- Re-run all negative tests (NT-1..NT-5) on the enhanced model.
- Record the extra GPU hours used (AC-4 resource envelope: the enhanced model is a new configuration and its extra cost must be shown).
- Never delete or overwrite the lean model, its data version, or its results.

### 14.5 Re-processing the completed area after promotion
- Re-run only what the enhancement affects (new dates, previously skipped tiles, changed model), not the whole history.
- Keep alert IDs stable: matched alerts are updated (new score, new evidence); new ones are added; disappeared ones are marked "withdrawn by v2" with the reason. Never silently delete alerts.
- Generate `reports/enhancement_<pack>.md`: what was added, size, GPU hours, KPI before vs after, alerts added/withdrawn, and a short conclusion. This becomes evidence for the final report and the paper.
