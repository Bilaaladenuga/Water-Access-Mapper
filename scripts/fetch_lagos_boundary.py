"""
Fetch the Lagos State boundary from OCHA HDX and save as GeoJSON.

Source: "Nigeria - Subnational Administrative Boundaries" (COD-AB)
https://data.humdata.org/dataset/cod-ab-nga
License: CC BY-IGO (attribution required)

Downloads the full Nigeria admin-1 GeoJSON zip, extracts Lagos State,
and writes it to data/processed/.

Usage:
    python scripts/fetch_lagos_boundary.py
"""

from __future__ import annotations

import io
import json
import pathlib
import sys
import urllib.request
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]

# Resource: nga_admin_boundaries.geojson.zip (GeoJSON)
HDX_URL = (
    "https://data.humdata.org/dataset/cod-ab-nga/resource/"
    "7e30ec96-7f29-4ee8-9f4c-77633b353cbb/download/nga_admin_boundaries.geojson.zip"
)

STATE_NAME = "Lagos"

OUT_RAW_DIR = ROOT / "data" / "raw" / "boundaries"
OUT_PROCESSED_DIR = ROOT / "data" / "processed" / "boundaries"
OUT_RAW_ZIP = OUT_RAW_DIR / "nga_admin_boundaries.geojson.zip"
OUT_GEOJSON = OUT_PROCESSED_DIR / "lagos_state.geojson"


def extract_state(feature_collection: dict, state_name: str) -> dict | None:
    """Return the admin-1 feature for state_name (e.g. 'Lagos')."""
    for feature in feature_collection.get("features", []):
        props = feature.get("properties", {})
        # admin-1 rows carry adm1_name; admin-2 rows also carry adm1_name
        # (the parent), so require that adm2_name is absent.
        if props.get("adm1_name") == state_name and not props.get("adm2_name"):
            return feature
    return None


def main() -> int:
    OUT_RAW_DIR.mkdir(parents=True, exist_ok=True)
    OUT_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    print(f"==> Downloading {HDX_URL}")
    with urllib.request.urlopen(HDX_URL, timeout=300) as resp:
        data = resp.read()
    OUT_RAW_ZIP.write_bytes(data)
    print(f"    saved {OUT_RAW_ZIP} ({len(data) / 1e6:.1f} MB)")

    print("==> Extracting admin-1 (states) layer")
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        with zf.open("nga_admin1.geojson") as f:
            states = json.load(f)
    print(f"    {len(states['features'])} states in file")

    lagos = extract_state(states, STATE_NAME)
    if lagos is None:
        print(f"ERROR: state {STATE_NAME!r} not found in admin-1 layer")
        return 1

    props = lagos["properties"]
    print(
        f"    found {STATE_NAME}: pcode={props.get('adm1_pcode')}, "
        f"area={props.get('area_sqkm')} km2, "
        f"center=({props.get('center_lon')}, {props.get('center_lat')})"
    )

    # Keep the raw feature as-is; add provenance for the processed file.
    processed = {"type": "FeatureCollection", "features": [lagos]}
    OUT_GEOJSON.write_text(json.dumps(processed), encoding="utf-8")
    print(f"==> Wrote {OUT_GEOJSON}")

    # Quick validation of the geometry.
    geom_type = lagos["geometry"]["type"]
    print(f"    geometry type: {geom_type}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
