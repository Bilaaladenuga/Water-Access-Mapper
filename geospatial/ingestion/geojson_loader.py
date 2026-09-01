"""
GeoJSON Loader — Water Access Mapper

Loads water point data from GeoJSON files into the database.
Handles validation, deduplication, and geometry cleaning.

Usage:
    python -m geospatial.ingestion.geojson_loader data/sample/water_points.geojson
"""

import json
from pathlib import Path
from shapely.geometry import shape, Point
from shapely.validation import make_valid


# Valid water types (matches database constraints)
VALID_WATER_TYPES = {"well", "tap", "spring", "borehole", "rainwater", "other"}

# Valid statuses
VALID_STATUSES = {"operational", "broken", "unknown", "abandoned"}

# Study area bounds for Lagos State (from GADM 4.1 official boundary)
# Actual bounds: lon 2.7063-4.3482, lat 6.3732-6.7070
STUDY_AREA_BOUNDS = {
    "min_lon": 2.7,
    "max_lon": 4.4,
    "min_lat": 6.35,
    "max_lat": 6.75,
}


def load_geojson(filepath: str) -> list[dict]:
    """
    Load features from a GeoJSON file.

    Returns a list of feature dictionaries with properties and geometry.
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    with open(filepath, "r") as f:
        data = json.load(f)

    if data.get("type") != "FeatureCollection":
        raise ValueError("File is not a GeoJSON FeatureCollection")

    features = data.get("features", [])
    print(f"Loaded {len(features)} features from {filepath.name}")
    return features


def validate_coordinates(lat: float, lon: float) -> list[str]:
    """
    Validate latitude and longitude coordinates.

    Returns a list of error messages (empty if valid).
    """
    errors = []

    if not (-90 <= lat <= 90):
        errors.append(f"Latitude {lat} out of range [-90, 90]")

    if not (-180 <= lon <= 180):
        errors.append(f"Longitude {lon} out of range [-180, 180]")

    # Check study area bounds (warning, not error)
    if not (
        STUDY_AREA_BOUNDS["min_lon"] <= lon <= STUDY_AREA_BOUNDS["max_lon"]
    ):
        errors.append(
            f"Longitude {lon} outside study area "
            f"[{STUDY_AREA_BOUNDS['min_lon']}, {STUDY_AREA_BOUNDS['max_lon']}]"
        )

    if not (
        STUDY_AREA_BOUNDS["min_lat"] <= lat <= STUDY_AREA_BOUNDS["max_lat"]
    ):
        errors.append(
            f"Latitude {lat} outside study area "
            f"[{STUDY_AREA_BOUNDS['min_lat']}, {STUDY_AREA_BOUNDS['max_lat']}]"
        )

    return errors


def validate_feature(feature: dict, index: int) -> list[str]:
    """
    Validate a single GeoJSON feature.

    Returns a list of error messages (empty if valid).
    """
    errors = []
    props = feature.get("properties", {})
    geom = feature.get("geometry", {})

    # Check geometry exists
    if not geom or not geom.get("coordinates"):
        errors.append(f"Feature {index}: Missing geometry")
        return errors

    # Check geometry type
    if geom.get("type") != "Point":
        errors.append(f"Feature {index}: Expected Point geometry, got {geom.get('type')}")
        return errors

    # Extract coordinates (GeoJSON is [lon, lat])
    coords = geom["coordinates"]
    if len(coords) < 2:
        errors.append(f"Feature {index}: Insufficient coordinates")
        return errors

    lon, lat = coords[0], coords[1]

    # Validate coordinates
    coord_errors = validate_coordinates(lat, lon)
    for err in coord_errors:
        errors.append(f"Feature {index} ({props.get('name', 'unnamed')}): {err}")

    # Validate water type
    water_type = props.get("water_type", "")
    if water_type not in VALID_WATER_TYPES:
        errors.append(
            f"Feature {index}: Invalid water_type '{water_type}'. "
            f"Valid: {VALID_WATER_TYPES}"
        )

    # Validate status
    status = props.get("status", "")
    if status and status not in VALID_STATUSES:
        errors.append(
            f"Feature {index}: Invalid status '{status}'. "
            f"Valid: {VALID_STATUSES}"
        )

    # Check name exists
    if not props.get("name"):
        errors.append(f"Feature {index}: Missing name")

    return errors


def clean_geometry(geometry: dict) -> dict:
    """
    Clean and validate geometry using Shapely.

    Returns cleaned geometry dict or None if invalid.
    """
    try:
        geom = shape(geometry)
        if not geom.is_valid:
            geom = make_valid(geom)
        if geom.is_empty:
            return None
        # Convert back to GeoJSON dict
        return json.loads(json.dumps(geom.__geo_interface__))
    except Exception:
        return None


def detect_duplicates(
    features: list[dict], threshold_meters: float = 50.0
) -> list[tuple[int, int]]:
    """
    Detect potential duplicate water points within a distance threshold.

    Returns list of (index_a, index_b) pairs that are close together.
    """
    duplicates = []
    points = []

    for i, feat in enumerate(features):
        geom = feat.get("geometry", {})
        coords = geom.get("coordinates", [None, None])
        if coords and len(coords) >= 2:
            points.append((i, Point(coords[0], coords[1])))

    # Compare each pair
    for i in range(len(points)):
        for j in range(i + 1, len(points)):
            idx_a, pt_a = points[i]
            idx_b, pt_b = points[j]
            # Approximate distance in degrees (~111km per degree)
            distance_deg = pt_a.distance(pt_b)
            distance_m = distance_deg * 111_000

            if distance_m < threshold_meters:
                duplicates.append((idx_a, idx_b))

    return duplicates


def process_geojson(filepath: str) -> dict:
    """
    Full ingestion pipeline for a GeoJSON file.

    Returns a summary dict with processed/valid/invalid/duplicate counts.
    """
    features = load_geojson(filepath)
    total = len(features)

    valid = []
    invalid = []
    all_errors = []

    for i, feature in enumerate(features):
        errors = validate_feature(feature, i)
        if errors:
            invalid.append(feature)
            all_errors.extend(errors)
        else:
            # Clean geometry
            cleaned_geom = clean_geometry(feature["geometry"])
            if cleaned_geom is None:
                invalid.append(feature)
                all_errors.append(f"Feature {i}: Invalid geometry after cleaning")
            else:
                feature["geometry"] = cleaned_geom
                valid.append(feature)

    # Detect duplicates
    duplicates = detect_duplicates(valid)

    summary = {
        "total_features": total,
        "valid_features": len(valid),
        "invalid_features": len(invalid),
        "duplicate_pairs": len(duplicates),
        "errors": all_errors,
        "valid_data": valid,
    }

    print(f"\nProcessing Summary:")
    print(f"  Total features: {total}")
    print(f"  Valid: {len(valid)}")
    print(f"  Invalid: {len(invalid)}")
    print(f"  Duplicate pairs: {len(duplicates)}")

    if all_errors:
        print(f"\nValidation Errors:")
        for err in all_errors:
            print(f"  - {err}")

    return summary


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m geospatial.ingestion.geojson_loader <filepath>")
        sys.exit(1)

    result = process_geojson(sys.argv[1])
