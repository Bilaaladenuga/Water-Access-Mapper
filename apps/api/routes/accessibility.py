"""
Accessibility Analysis Routes — Water Access Mapper

Provides configurable accessibility analysis:
- Distance-based categories (0-500m, 500m-1km, etc.)
- Accessibility scoring for grid cells
- Underserved area identification
- Point-in-polygon analysis for study area coverage
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import text
from database import async_session_factory

router = APIRouter(prefix="/api/accessibility", tags=["accessibility"])


class AccessibilityCategory(BaseModel):
    label: str
    min_meters: float
    max_meters: float
    count: int
    percentage: float


class AccessibilityResponse(BaseModel):
    total_cells: int
    total_points: int
    categories: list[AccessibilityCategory]
    underserved_cells: list[dict]
    underserved_percentage: float
    accessibility_score: float


class UnderservedArea(BaseModel):
    latitude: float
    longitude: float
    nearest_water_distance: float
    category: str
    severity: str


# Default accessibility categories (in meters)
DEFAULT_CATEGORIES = [
    {"label": "Excellent (0-500m)", "min": 0, "max": 500},
    {"label": "Good (500m-1km)", "min": 500, "max": 1000},
    {"label": "Moderate (1-2km)", "min": 1000, "max": 2000},
    {"label": "Poor (2-5km)", "min": 2000, "max": 5000},
    {"label": "Critical (>5km)", "min": 5000, "max": 999999},
]


def _get_category(distance: float, categories: list[dict]) -> str:
    for cat in categories:
        if cat["min"] <= distance < cat["max"]:
            return cat["label"]
    return categories[-1]["label"] if categories else "Unknown"


async def _get_water_points():
    """Fetch all water point geometries from database."""
    query = """
        SELECT id, name, water_type, status, latitude, longitude,
               ST_X(geometry) AS lon, ST_Y(geometry) AS lat
        FROM water_points
    """
    async with async_session_factory() as session:
        result = await session.execute(text(query))
        return result.fetchall()


@router.get("/analysis")
async def accessibility_analysis(
    grid_size: float = Query(0.05, description="Grid cell size in degrees (~5km at equator)"),
    categories_json: str | None = Query(
        None,
        description='Custom categories as JSON: [{"label":"Name","min":0,"max":500}]'
    ),
):
    """
    Perform accessibility analysis across the study area.

    Uses Python-based grid generation and Shapely distance calculations.
    Grid cells are classified by distance to nearest water point.
    """
    import json

    if categories_json:
        try:
            categories = json.loads(categories_json)
        except json.JSONDecodeError:
            categories = DEFAULT_CATEGORIES
    else:
        categories = DEFAULT_CATEGORIES

    # Get all water points
    points = await _get_water_points()
    if not points:
        return {"error": "No water points found"}

    total_points = len(points)

    # Get bounding box
    lons = [float(p[6]) for p in points]
    lats = [float(p[7]) for p in points]
    min_lon, max_lon = min(lons), max(lons)
    min_lat, max_lat = min(lats), max(lats)

    # Generate grid in Python
    grid_lons = []
    lon_val = min_lon
    while lon_val <= max_lon:
        grid_lons.append(lon_val)
        lon_val += grid_size

    grid_lats = []
    lat_val = min_lat
    while lat_val <= max_lat:
        grid_lats.append(lat_val)
        lat_val += grid_size

    # Calculate distance from each grid cell to nearest water point
    # Using Haversine formula (fast, no library needed)
    import math

    def haversine(lat1, lon1, lat2, lon2):
        R = 6371000  # Earth radius in meters
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    categorized = {cat["label"]: 0 for cat in categories}
    underserved = []
    total_cells = 0

    for glon in grid_lons:
        for glat in grid_lats:
            total_cells += 1
            min_dist = float("inf")
            for p in points:
                dist = haversine(glat, glon, float(p[7]), float(p[6]))
                if dist < min_dist:
                    min_dist = dist
            min_dist = round(min_dist, 1)

            for cat in categories:
                if cat["min"] <= min_dist < cat["max"]:
                    categorized[cat["label"]] += 1
                    break

            if min_dist >= 2000:
                severity = "critical" if min_dist >= 5000 else "moderate" if min_dist >= 3000 else "low"
                underserved.append({
                    "latitude": glat,
                    "longitude": glon,
                    "nearest_water_distance": min_dist,
                    "category": _get_category(min_dist, categories),
                    "severity": severity,
                })

    # Build category results
    category_results = []
    for cat in categories:
        count = categorized.get(cat["label"], 0)
        percentage = round((count / total_cells * 100), 1) if total_cells > 0 else 0
        category_results.append(AccessibilityCategory(
            label=cat["label"],
            min_meters=cat["min"],
            max_meters=cat["max"],
            count=count,
            percentage=percentage,
        ))

    # Accessibility score: % of cells within 1km
    good_cells = sum(categorized.get(cat["label"], 0) for cat in categories if cat["max"] <= 1000)
    accessibility_score = round((good_cells / total_cells * 100), 1) if total_cells > 0 else 0

    underserved_count = len(underserved)
    underserved_pct = round((underserved_count / total_cells * 100), 1) if total_cells > 0 else 0

    # Sort underserved by distance descending, keep top 50
    underserved.sort(key=lambda x: x["nearest_water_distance"], reverse=True)

    return AccessibilityResponse(
        total_cells=total_cells,
        total_points=total_points,
        categories=category_results,
        underserved_cells=underserved[:50],
        underserved_percentage=underserved_pct,
        accessibility_score=accessibility_score,
    )


@router.get("/underserved")
async def get_underserved_areas(
    threshold_meters: float = Query(2000, description="Distance threshold for underserved"),
):
    """
    Identify grid cells that are far from any water point.
    """
    points = await _get_water_points()
    if not points:
        return {"error": "No water points found"}

    lons = [float(p[6]) for p in points]
    lats = [float(p[7]) for p in points]
    min_lon, max_lon = min(lons), max(lons)
    min_lat, max_lat = min(lats), max(lats)

    grid_size = 0.05
    grid_lons = []
    lon_val = min_lon
    while lon_val <= max_lon:
        grid_lons.append(lon_val)
        lon_val += grid_size

    grid_lats = []
    lat_val = min_lat
    while lat_val <= max_lat:
        grid_lats.append(lat_val)
        lat_val += grid_size

    import math

    def haversine(lat1, lon1, lat2, lon2):
        R = 6371000
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    areas = []
    for glon in grid_lons:
        for glat in grid_lats:
            min_dist = float("inf")
            for p in points:
                dist = haversine(glat, glon, float(p[7]), float(p[6]))
                if dist < min_dist:
                    min_dist = dist
            if min_dist > threshold_meters:
                severity = "critical" if min_dist >= 5000 else "moderate" if min_dist >= 3000 else "low"
                areas.append(UnderservedArea(
                    latitude=glat,
                    longitude=glon,
                    nearest_water_distance=round(min_dist, 1),
                    category=_get_category(min_dist, DEFAULT_CATEGORIES),
                    severity=severity,
                ))

    areas.sort(key=lambda a: a.nearest_water_distance, reverse=True)

    critical = sum(1 for a in areas if a.severity == "critical")
    moderate = sum(1 for a in areas if a.severity == "moderate")
    low = sum(1 for a in areas if a.severity == "low")

    return {
        "underserved_areas": [a.model_dump() for a in areas],
        "summary": {
            "total_underserved": len(areas),
            "critical": critical,
            "moderate": moderate,
            "low": low,
            "threshold_meters": threshold_meters,
        },
    }


@router.get("/point-analysis")
async def point_accessibility(
    lat: float = Query(..., description="Latitude to analyze"),
    lon: float = Query(..., description="Longitude to analyze"),
):
    """
    Analyze accessibility for a specific point.
    Returns distance to nearest water point, accessibility category,
    and nearby water points within 2km.
    """
    params = {"lon": lon, "lat": lat}

    nearest_query = """
        SELECT id, name, water_type, status, latitude, longitude,
               ST_Distance(
                   geometry::geography,
                   ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
               ) AS distance
        FROM water_points
        ORDER BY geometry <-> ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)
        LIMIT 1
    """

    nearby_query = """
        SELECT id, name, water_type, status, latitude, longitude,
               ST_Distance(
                   geometry::geography,
                   ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
               ) AS distance
        FROM water_points
        WHERE ST_DWithin(
            geometry::geography,
            ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
            2000
        )
        ORDER BY distance
    """

    async with async_session_factory() as session:
        nearest_result = await session.execute(text(nearest_query), params)
        nearest = nearest_result.fetchone()

        nearby_result = await session.execute(text(nearby_query), params)
        nearby_rows = nearby_result.fetchall()

    if not nearest:
        return {"error": "No water points found"}

    nearest_distance = float(nearest[6])
    category = _get_category(nearest_distance, DEFAULT_CATEGORIES)

    nearby = []
    for row in nearby_rows:
        nearby.append({
            "id": str(row[0]),
            "name": row[1],
            "water_type": row[2],
            "status": row[3],
            "latitude": float(row[4]),
            "longitude": float(row[5]),
            "distance_meters": round(float(row[6]), 1),
        })

    return {
        "query_point": {"latitude": lat, "longitude": lon},
        "nearest_water_point": {
            "id": str(nearest[0]),
            "name": nearest[1],
            "water_type": nearest[2],
            "status": nearest[3],
            "latitude": float(nearest[4]),
            "longitude": float(nearest[5]),
            "distance_meters": round(nearest_distance, 1),
        },
        "accessibility_category": category,
        "nearby_within_2km": nearby,
        "nearby_count": len(nearby),
    }
