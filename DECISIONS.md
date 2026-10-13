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
- **Status:** Proposed — waiting on user (Section 13 batch 1, Q6)
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
- **Status:** Proposed (2026-10-14) — will be confirmed in question batch 2
- **Decision (provisional):** Monitoring dates 2022–2026, 2 per year (pre-monsoon Mar–May, post-monsoon Oct–Dec) · KL University report/slide templates unknown → generic IEEE-style report until a template arrives · research paper target: yes, draft in CP2.
- **Consequence:** Week 1 work isn't blocked; all three are config/doc changes, cheap to redo.
