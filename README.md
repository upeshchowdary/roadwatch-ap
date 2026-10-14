# RoadWatch AP

Automatic road extraction and **new-road change alerting** from multi-date satellite imagery,
built for Andhra Pradesh and designed to scale to India (SIH1564 / NTRO problem; KL University capstone).

- **Tier 1:** Sentinel-2 (10 m optical) + Sentinel-1 (radar) statewide screening, streamed tile by tile.
- **Tier 2:** high-res verification in three 20×20 km pilot zones (NTR/Krishna districts).
- **Core idea:** compare road *graphs* across dates, with a persistence rule and abstain mode, to
  keep false alerts low.

## Quick start (Windows PowerShell)

```powershell
uv sync                                   # Python 3.11 env (uv)
uv run roadwatch info                     # validate config, show AOI / tiles / splits
uv run roadwatch holdout check            # verify the frozen test set is unchanged
uv run pytest                             # tests
uv run python scripts/check_env.py        # which keys are set (PRESENT/MISSING only)
uv run python scripts/disk_check.py       # disk guard
```

## Layout

See `PROJECT_PROMPT.md` Section 5. Status: `PROGRESS.md`. Decisions: `DECISIONS.md`.
Data licences: `LICENSES_DATA.md`. Evidence: `evidence/manifest.csv`.

## Attribution

Boundaries and road labels © OpenStreetMap contributors (ODbL). Contains modified Copernicus
Sentinel data. No ISRO/Bhoonidhi imagery is stored in this public repository.
