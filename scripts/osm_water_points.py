"""
OSM Water Point Loader — Water Access Mapper (Expanded)

Downloads real water point data from OpenStreetMap via the Overpass API.
Expanded to query more tags for comprehensive coverage of Lagos State.

Usage:
    python scripts/osm_water_points.py

Data sources queried:
    - amenity=drinking_water (public drinking fountains)
    - amenity=water_point (general water points)
    - man_made=water_well (wells)
    - man_made=water_tap (public taps)
    - man_made=water_tank (water tanks/stations)
    - waterway=water_point (general water points)
    - natural=spring (natural springs)
"""

import json
import pathlib
import sys
import time
import urllib.request
import urllib.parse


# Overpass API endpoints (mirrors for fallback)
OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]
OVERPASS_URL = OVERPASS_URLS[0]

# Lagos State bounding box chunks — expanded to cover entire state
# Format: south,west,north,east
LAGOS_CHUNKS = [
    # Lagos Island / Mainland (dense urban core)
    "6.40,3.30,6.52,3.45",
    # Victoria Island / Lekki Phase 1
    "6.40,3.40,6.46,3.50",
    # Ikoyi / Ebute Metta / Yaba
    "6.45,3.35,6.52,3.42",
    # Surulere / Mushin / Oshodi
    "6.50,3.30,6.57,3.38",
    # Ikeja / Maryland / Anthony
    "6.55,3.30,6.63,3.40",
    # Agege / Iyana-Ipaja / Abule-Egba
    "6.60,3.25,6.68,3.35",
    # Lekki Phase 2 / Ajah
    "6.42,3.47,6.50,3.58",
    # Ikorodu
    "6.57,3.48,6.70,3.65",
    # Badagry / Ojo / Festac
    "6.38,2.95,6.50,3.25",
    # Epe / Ibeju-Lekki
    "6.48,3.60,6.65,3.95",
    # Apapa / Tin Can Island
    "6.42,3.25,6.48,3.38",
    # Coker / Aguda / Orile
    "6.45,3.28,6.52,3.35",
    # Iganmu / Badagry Corridor
    "6.45,3.00,6.52,3.20",
    # Alimosho / Igando
    "6.52,3.20,6.60,3.30",
    # Ketu / Mile 12 / Ikorodu Road
    "6.55,3.35,6.62,3.48",
]

# OSM tags that indicate water points — expanded list
WATER_POINT_TAGS = [
    '["amenity"="drinking_water"]',
    '["amenity"="water_point"]',
    '["man_made"="water_well"]',
    '["man_made"="water_tap"]',
    '["man_made"="water_tank"]',
    '["waterway"="water_point"]',
    '["natural"="spring"]',
]


def build_overpass_query(bbox: str) -> str:
    """Build an Overpass QL query for water points within a bounding box."""
    tags = "\n  ".join(
        f"node{tag}({bbox});" for tag in WATER_POINT_TAGS
    )
    return f"""
[out:json][timeout:30];
(
  {tags}
);
out body;
""".strip()


def fetch_osm_data(query: str) -> dict:
    """Fetch data from the Overpass API, trying mirrors on failure."""
    headers = {
        "User-Agent": "WaterAccessMapper/1.0 (portfolio-project)"
    }

    encoded_query = urllib.parse.urlencode({"data": query}).encode()

    for url in OVERPASS_URLS:
        try:
            req = urllib.request.Request(
                url,
                data=encoded_query,
                headers=headers,
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read())
            return result
        except Exception as e:
            print(f"    Mirror {url} failed: {e}")
            continue

    raise Exception("All Overpass mirrors failed")


def parse_osm_element(element: dict) -> dict | None:
    """Convert an OSM element to a water point feature dict."""
    tags = element.get("tags", {})
    lat = element.get("lat")
    lon = element.get("lon")

    if lat is None or lon is None:
        return None

    # Determine water type from OSM tags
    water_type = "tap"  # default
    if tags.get("amenity") == "drinking_water":
        water_type = "tap"
    elif tags.get("amenity") == "water_point":
        water_type = "tap"
    elif tags.get("man_made") == "water_well":
        water_type = "well"
    elif tags.get("man_made") == "water_tap":
        water_type = "tap"
    elif tags.get("man_made") == "water_tank":
        water_type = "borehole"
    elif tags.get("waterway") == "water_point":
        water_type = "tap"
    elif tags.get("natural") == "spring":
        water_type = "spring"

    # Build name from OSM tags
    name = (
        tags.get("name")
        or tags.get("name:en")
        or tags.get("description")
        or f"OSM Water Point {element.get('id', 'unknown')}"
    )

    return {
        "osm_id": element.get("id"),
        "name": name,
        "water_type": water_type,
        "status": "unknown",
        "source": "osm",
        "latitude": lat,
        "longitude": lon,
        "osm_tags": {k: v for k, v in tags.items() if k not in ("name", "name:en")},
    }


def convert_to_geojson(osm_data: dict) -> list[dict]:
    """Convert Overpass API response to list of GeoJSON features."""
    features = []
    for element in osm_data.get("elements", []):
        feature = parse_osm_element(element)
        if feature:
            features.append({
                "type": "Feature",
                "properties": {
                    "name": feature["name"],
                    "water_type": feature["water_type"],
                    "status": feature["status"],
                    "source": feature["source"],
                    "latitude": feature["latitude"],
                    "longitude": feature["longitude"],
                    "osm_id": feature["osm_id"],
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [feature["longitude"], feature["latitude"]],
                },
            })
    return features


def download_osm_water_points(save_path: str = "data/raw/osm_water_points.geojson") -> str:
    """Full pipeline: query OSM, convert to GeoJSON, save to file."""
    all_features = []
    seen_ids = set()
    errors = 0

    for i, bbox in enumerate(LAGOS_CHUNKS):
        print(f"Chunk {i + 1}/{len(LAGOS_CHUNKS)} (bbox: {bbox})")
        query = build_overpass_query(bbox)

        try:
            osm_data = fetch_osm_data(query)
            chunk_features = convert_to_geojson(osm_data)

            new_count = 0
            for feat in chunk_features:
                osm_id = feat["properties"].get("osm_id")
                if osm_id and osm_id not in seen_ids:
                    seen_ids.add(osm_id)
                    all_features.append(feat)
                    new_count += 1

            print(f"  +{new_count} new (total unique: {len(all_features)})")
        except Exception as e:
            errors += 1
            print(f"  ERROR: {e}")
            if errors >= 3:
                print("  Too many errors, stopping.")
                break

        # Be polite to the Overpass API — longer delay to avoid 429
        time.sleep(3)

    geojson = {
        "type": "FeatureCollection",
        "name": "osm_water_points_lagos",
        "features": all_features,
    }

    save_path = pathlib.Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    with open(save_path, "w") as f:
        json.dump(geojson, f, indent=2)

    print(f"\nTotal unique water points: {len(all_features)}")
    print(f"Saved to: {save_path}")

    # Summary by type
    types = {}
    for feat in all_features:
        wt = feat["properties"]["water_type"]
        types[wt] = types.get(wt, 0) + 1
    print("\nBy type:")
    for wt, count in sorted(types.items()):
        print(f"  {wt}: {count}")

    return str(save_path)


if __name__ == "__main__":
    download_osm_water_points()
