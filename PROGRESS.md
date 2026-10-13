# PROGRESS — RoadWatch AP

> Living log. Read this and `DECISIONS.md` at the start of every session.
> Format per entry: date · what was done · evidence. Newest status block on top.

## Current status (2026-10-14)

- **Phase:** Section 0 — kick-off (before Week 1)
- **CP1 target:** 4 weeks from kick-off (exact review date: waiting on answer)
- **Blockers:** waiting on Section 13 answers (batch 1 sent 2026-10-14)

## Done

### 2026-10-14 — Section 0.1 kick-off
- Read `PROJECT_PROMPT.md` in full.
- Machine check (evidence below).
- Created `PROGRESS.md`, `DECISIONS.md`, `.gitignore`; initialised Git; first commit.
- Sent Section 13 questions batch 1 (6 questions). Provisional defaults for the other 3 recorded in `DECISIONS.md` (ADR-005).

#### Machine check evidence
| Item | Result |
|---|---|
| OS | Windows 11 Home 10.0.26300 |
| PowerShell | 5.1 (Windows PowerShell; no PowerShell 7) |
| CPU / RAM | i9-13900HX / 15.7 GB (≈3 GB free at check time) |
| GPU | NVIDIA RTX 4070 Laptop, 8 GB VRAM, driver 592.82 (+ Intel UHD) |
| Disk free | C: 19.2 GB · D: 209.7 GB · **E: 249.9 GB (project drive)** |
| Python | system 3.13.7; uv-managed 3.12.14; 3.10.11. **3.11 not installed yet** |
| uv | 0.12.5 |
| Git | 2.55.0, global identity set |
| Node / npm | 24.21.0 / 12.0.2 |
| Kaggle CLI | not installed (will install inside the project env) |

## Next
1. Get Section 13 answers → update this file.
2. Show Week 1 plan and start: repo skeleton, uv env (Python 3.11), `.env.example`, `scripts/check_env.py`, `scripts/disk_check.py`, CI, account walkthroughs.

## Blockers / waiting on user
- Section 13 batch 1 answers.
