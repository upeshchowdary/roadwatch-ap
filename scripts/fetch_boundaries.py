"""Fetch AOI boundary polygons from OpenStreetMap (via Nominatim lookup by relation ID).

Usage:  uv run python scripts/fetch_boundaries.py
Output: configs/boundaries/<name>.geojson  (EPSG:4326, simplified ~50 m)
        configs/boundaries/ntr_krishna.geojson  (union of the two pilot districts)
Licence: OpenStreetMap contributors, ODbL 1.0 (see LICENSES_DATA.md).

Relation IDs were looked up on 2026-10-14 (Overpass is_in / Nominatim search):
  Andhra Pradesh 2022095 (Q1159) · NTR district 14000341 (Q110876763) · Krishna district 2022135
"""

from __future__ import annotations

import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import geopandas as gpd
import requests
from shapely.geometry import MultiPolygon, Polygon, shape
from shapely.ops import unary_union

NOMINATIM = "https://nominatim.openstreetmap.org/lookup"
HEADERS = {"User-Agent": "RoadWatchAP-capstone/0.1 (KL University student project)"}
ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "configs" / "boundaries"

RELATIONS = {
    "andhra_pradesh": 2022095,
    "ntr_district": 14000341,
    "krishna_district": 2022135,
}
METRIC_CRS = "EPSG:32644"  # UTM 44N, only used to report area


def fetch_relation(rel_id: int) -> tuple[MultiPolygon, dict]:
    r = requests.get(
        NOMINATIM,
        params={"osm_ids": f"R{rel_id}", "format": "geojson", "polygon_geojson": 1},
        headers=HEADERS,
        timeout=120,
    )
    r.raise_for_status()
    feats = r.json()["features"]
    if len(feats) != 1:
        raise RuntimeError(f"relation {rel_id}: expected 1 feature, got {len(feats)}")
    geom = shape(feats[0]["geometry"])
    if isinstance(geom, Polygon):
        geom = MultiPolygon([geom])
    return geom, feats[0]["properties"]


def save(name: str, geom, props: dict) -> None:
    gdf = gpd.GeoDataFrame(
        {
            "name": [name],
            "osm_relation_id": [props.get("osm_id")],
            "display_name": [props.get("display_name")],
            "source": ["OpenStreetMap (Nominatim lookup)"],
            "licence": ["ODbL-1.0, (c) OpenStreetMap contributors"],
            "access_date": [datetime.now(UTC).date().isoformat()],
        },
        geometry=[geom],
        crs="EPSG:4326",
    )
    area_km2 = gdf.to_crs(METRIC_CRS).area.iloc[0] / 1e6
    gdf["geometry"] = gdf.geometry.simplify(0.0005, preserve_topology=True)
    out = OUT_DIR / f"{name}.geojson"
    out.write_text(json.dumps(json.loads(gdf.to_json()), separators=(",", ":")), encoding="utf-8")
    print(f"[{name}] area={area_km2:,.0f} km2 -> {out.relative_to(ROOT)}")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    geoms = {}
    for name, rel_id in RELATIONS.items():
        geom, props = fetch_relation(rel_id)
        props.setdefault("osm_id", rel_id)
        save(name, geom, props)
        geoms[name] = geom
        time.sleep(1.1)  # Nominatim usage policy: max 1 request/second
    pilot = unary_union([geoms["ntr_district"], geoms["krishna_district"]])
    save("ntr_krishna", pilot, {"osm_id": "14000341+2022135", "display_name": "NTR + Krishna"})
    return 0


if __name__ == "__main__":
    sys.exit(main())
