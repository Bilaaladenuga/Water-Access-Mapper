"""
OSM Water Point Loader — Water Access Mapper

Downloads real water point data from OpenStreetMap via the Overpass API.
Converts OSM data to GeoJSON format for ingestion into PostGIS.

Usage:
    python -m geospatial.ingestion.osm_loader

Data sources queried:
    - amenity=drinking_water (public drinking fountains)
    - man_made=water_well (wells)
    - man_made=water_tap (public taps)
    - waterway=water_point (general water points)
"""

import json
import urllib.request
import urllib.parse
from pathlib import Path
import httpx


# Overpass API endpoint
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Lagos State bounding box for Overpass queries
# Format: south,west,north,east
LAGOS_BBOX = "6.22,2.68,6.90,4.35"

# Smaller chunks for reliable querying
LAGOS_CHUNKS = [
    "6.35,3.20,6.55,3.45",  # Lagos Island / Mainland
    "6.55,3.20,6.70,3.45",  # Ikeja / Agege
    "6.40,3.45,6.55,3.65",  # Lekki / Ajah
    "6.55,3.45,6.70,3.65",  # Ikorodu
    "6.35,3.00,6.50,3.20",  # Badagry / Ojo
]

# OSM tags that indicate water points
WATER_POINT_TAGS = [
    '["amenity"="drinking_water"]',
    '["man_made"="water_well"]',
    '["man_made"="water_tap"]',
    '["waterway"="water_point"]',
]


def build_overpass_query(bbox: str) -> str:
    """
    Build an Overpass QL query for water points within a bounding box.

    Returns the query string for the Overpass API.
    """
    tags = "\n  ".join(
        f'node{tag}({bbox});' for tag in WATER_POINT_TAGS
    )

    query = f"""
[out:json][timeout:30];
(
  {tags}
);
out body;
""".strip()

    return query


def fetch_osm_data(query: str) -> dict:
    """
    Fetch data from the Overpass API.

    Returns the parsed JSON response.
    """
    print(f"Querying Overpass API...")
    print(f"  URL: {OVERPASS_URL}")
    print(f"  Water point tags: {len(WATER_POINT_TAGS)}")

    headers = {
        "User-Agent": "WaterAccessMapper/1.0 (portfolio-project)"
    }

    with httpx.Client(timeout=60) as client:
        response = client.post(
            OVERPASS_URL,
            data={"data": query},
            headers=headers,
        )
        response.raise_for_status()
        result = response.json()

    elements = result.get("elements", [])
    print(f"  Received {len(elements)} elements from OSM")
    return result


def parse_osm_element(element: dict) -> dict | None:
    """
    Convert an OSM element to a water point feature dict.

    Returns a dict with properties and geometry, or None if invalid.
    """
    tags = element.get("tags", {})
    lat = element.get("lat")
    lon = element.get("lon")

    if lat is None or lon is None:
        return None

    # Determine water type from OSM tags
    water_type = "other"
    if tags.get("amenity") == "drinking_water":
        water_type = "tap"
    elif tags.get("man_made") == "water_well":
        water_type = "well"
    elif tags.get("man_made") == "water_tap":
        water_type = "tap"
    elif tags.get("waterway") == "water_point":
        water_type = "tap"

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
        "status": "unknown",  # OSM doesn't track operational status
        "source": "osm",
        "latitude": lat,
        "longitude": lon,
        "osm_tags": {k: v for k, v in tags.items() if k not in ("name", "name:en")},
    }


def convert_to_geojson(osm_data: dict) -> dict:
    """
    Convert Overpass API response to GeoJSON FeatureCollection.
    """
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

    geojson = {
        "type": "FeatureCollection",
        "name": "osm_water_points_lagos",
        "features": features,
    }

    return geojson


def download_osm_water_points(
    save_path: str = "data/raw/osm_water_points.geojson",
) -> str:
    """
    Full pipeline: query OSM, convert to GeoJSON, save to file.

    Queries Lagos in smaller chunks to avoid API timeouts.
    Returns the path to the saved file.
    """
    all_features = []
    seen_ids = set()

    for i, bbox in enumerate(LAGOS_CHUNKS):
        print(f"\n--- Chunk {i + 1}/{len(LAGOS_CHUNKS)} (bbox: {bbox}) ---")
        query = build_overpass_query(bbox)

        try:
            osm_data = fetch_osm_data(query)
            chunk_geojson = convert_to_geojson(osm_data)

            for feat in chunk_geojson["features"]:
                osm_id = feat["properties"].get("osm_id")
                if osm_id and osm_id not in seen_ids:
                    seen_ids.add(osm_id)
                    all_features.append(feat)

            print(f"  Added {len(chunk_geojson['features'])} features (unique so far: {len(all_features)})")
        except Exception as e:
            print(f"  Error: {e}")
            print(f"  Skipping chunk {i + 1}...")

    geojson = {
        "type": "FeatureCollection",
        "name": "osm_water_points_lagos",
        "features": all_features,
    }

    # Save to file
    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)

    with open(save_path, "w") as f:
        json.dump(geojson, f, indent=2)

    print(f"\nResults:")
    print(f"  Total unique water points: {len(all_features)}")
    print(f"  Saved to: {save_path}")

    # Summary by type
    types = {}
    for feat in all_features:
        wt = feat["properties"]["water_type"]
        types[wt] = types.get(wt, 0) + 1

    print(f"\nBy type:")
    for wt, count in sorted(types.items()):
        print(f"  {wt}: {count}")

    return str(save_path)


if __name__ == "__main__":
    download_osm_water_points()
