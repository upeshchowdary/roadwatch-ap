# Data & model licences

Rules (PROJECT_PROMPT.md Section 2): attribute ODbL sources, respect Copernicus terms, never
publish ISRO/Bhoonidhi imagery publicly (this repo is **public**), respect the DINOv3 licence.
Status: ✅ verified · ⏳ to verify before use. Every row also appears in `evidence/manifest.csv`.

| Source | Used for | Licence / terms | Attribution text | Public repo OK? | Status |
|---|---|---|---|---|---|
| OpenStreetMap (boundaries, roads, history) | AOI boundaries, road labels, change labels | ODbL 1.0 | "© OpenStreetMap contributors" | Yes, with attribution; derived DBs stay ODbL | ✅ |
| Sentinel-2 L2A, Sentinel-1 RTC (via Microsoft Planetary Computer) | imagery, Tier 1 | Copernicus Sentinel data terms (free, open, attribution) | "Contains modified Copernicus Sentinel data [year]" | Yes | ✅ |
| Microsoft Road Detections | extra labels | ODbL 1.0 | "© Microsoft, ODbL" | Yes, with attribution | ⏳ |
| DeepGlobe Roads | Baseline A training | DeepGlobe 2018 challenge terms (research use) | cite Demir et al., CVPR-W 2018 | Do not re-host imagery | ⏳ |
| Massachusetts Roads | extra training | research use (Mnih, 2013) | cite Mnih PhD thesis 2013 | Do not re-host imagery | ⏳ |
| SpaceNet 3 | graph metrics (APLS) | CC BY-SA 4.0 | "SpaceNet, CC BY-SA 4.0" | Yes, share-alike | ⏳ |
| DINOv3 sat weights (`facebook/dinov3-vitl16-pretrain-sat493m`) | Reference B backbone | DINOv3 License (gated on Hugging Face) | per licence | Do not re-host weights | ⏳ |
| EOX Sentinel-2 Cloudless basemap | web basemap | CC BY-NC-SA 4.0 (2016) / CC BY 4.0 (later years) — check the year used | "Sentinel-2 cloudless by EOX" | Yes, with attribution | ⏳ |
| OpenFreeMap | web basemap | free, OSM-based | "© OpenFreeMap © OpenStreetMap contributors" | Yes | ⏳ |
| ISRO Bhoonidhi / NRSC high-res | Tier 2 verification | ISRO/NRSC terms | per terms | **NO — never commit or publish** | ⏳ |
| Google Earth Pro historical imagery | visual reference only | Google terms — no training, no redistribution | — | **NO** | ✅ (reference only) |
