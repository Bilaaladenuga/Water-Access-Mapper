"""
Routing API Routes — Water Access Mapper

Provides OSRM-based walking route calculation:
- Route from user location to nearest water point
- Route geometry for map display
- Distance and estimated walking time
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import text
from database import async_session_factory
import httpx

router = APIRouter(prefix="/api/routing", tags=["routing"])

# OSRM public demo server (for development)
# In production, you'd self-host OSRM or use a paid service
OSRM_BASE_URL = "https://router.project-osrm.org"


class RouteStep(BaseModel):
    instruction: str
    distance_meters: float
    duration_seconds: float


class RouteResponse(BaseModel):
    # Route to nearest water point
    nearest_point_id: str
    nearest_point_name: str
    nearest_point_lat: float
    nearest_point_lon: float

    # Route geometry (GeoJSON LineString)
    route_geometry: dict

    # Distances
    network_distance_meters: float
    straight_line_distance_meters: float

    # Walking time estimates
    walking_time_seconds: float
    walking_time_minutes: float

    # Route details
    steps: list[RouteStep]


async def fetch_osrm_route(
    origin_lon: float, origin_lat: float,
    dest_lon: float, dest_lat: float,
) -> dict | None:
    """
    Fetch a walking route from OSRM.

    OSRM format: lon,lat;lon,lat (longitude first!)
    """
    url = (
        f"{OSRM_BASE_URL}/route/v1/foot/"
        f"{origin_lon},{origin_lat};{dest_lon},{dest_lat}"
        f"?overview=full&geometries=geojson&steps=true"
    )

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, headers={"User-Agent": "WaterAccessMapper/0.1"})
        if resp.status_code != 200:
            return None
        data = resp.json()
        if data.get("code") != "Ok" or not data.get("routes"):
            return None
        return data["routes"][0]


def parse_osrm_route(route_data: dict) -> tuple[list[RouteStep], float, float]:
    """Parse OSRM route into steps, distance, and duration."""
    steps = []
    for leg in route_data.get("legs", []):
        for step in leg.get("steps", []):
            maneuver = step.get("maneuver", {})
            modifier = maneuver.get("modifier", "")
            type_ = maneuver.get("type", "")
            instruction = f"{type_}"
            if modifier:
                instruction = f"{type_} {modifier}"

            steps.append(RouteStep(
                instruction=instruction,
                distance_meters=round(step.get("distance", 0), 1),
                duration_seconds=round(step.get("duration", 0), 1),
            ))

    distance = route_data.get("distance", 0)
    duration = route_data.get("duration", 0)
    return steps, distance, duration


@router.get("/to-nearest")
async def get_route_to_nearest(
    lat: float = Query(..., description="User latitude"),
    lon: float = Query(..., description="User longitude"),
    water_type: str | None = Query(None, description="Filter by water type"),
    status: str | None = Query(None, description="Filter by status"),
):
    """
    Get a walking route from the user's location to the nearest water point.

    Uses OSRM foot profile for realistic walking routes on OSM road network.
    Returns route geometry, distance, and estimated walking time.
    """
    # Step 1: Find nearest water point
    conditions = []
    params: dict = {"lon": lon, "lat": lat}

    if water_type:
        conditions.append("water_type = :water_type")
        params["water_type"] = water_type
    if status:
        conditions.append("status = :status")
        params["status"] = status

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    nearest_query = f"""
        SELECT id, name, water_type, status, latitude, longitude,
               ST_Distance(
                   geometry::geography,
                   ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
               ) AS straight_distance
        FROM water_points
        {where_clause}
        ORDER BY geometry <-> ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)
        LIMIT 1
    """

    async with async_session_factory() as session:
        result = await session.execute(text(nearest_query), params)
        row = result.fetchone()

    if not row:
        return {"error": "No water points found matching criteria"}

    point_id = str(row[0])
    point_name = row[1]
    point_lat = float(row[4])
    point_lon = float(row[5])
    straight_distance = float(row[6])

    # Step 2: Get OSRM walking route
    route_data = await fetch_osrm_route(lon, lat, point_lon, point_lat)

    if not route_data:
        # Fallback: return straight line if OSRM fails
        # Walking speed ~5 km/h = 1.39 m/s
        walking_time = straight_distance / 1.39
        return RouteResponse(
            nearest_point_id=point_id,
            nearest_point_name=point_name,
            nearest_point_lat=point_lat,
            nearest_point_lon=point_lon,
            route_geometry={
                "type": "LineString",
                "coordinates": [[lon, lat], [point_lon, point_lat]],
            },
            network_distance_meters=round(straight_distance, 1),
            straight_line_distance_meters=round(straight_distance, 1),
            walking_time_seconds=round(walking_time, 1),
            walking_time_minutes=round(walking_time / 60, 1),
            steps=[],
        )

    steps, network_distance, walking_time = parse_osrm_route(route_data)

    # Get route geometry
    geometry = route_data.get("geometry", {"type": "LineString", "coordinates": []})

    return RouteResponse(
        nearest_point_id=point_id,
        nearest_point_name=point_name,
        nearest_point_lat=point_lat,
        nearest_point_lon=point_lon,
        route_geometry=geometry,
        network_distance_meters=round(network_distance, 1),
        straight_line_distance_meters=round(straight_distance, 1),
        walking_time_seconds=round(walking_time, 1),
        walking_time_minutes=round(walking_time / 60, 1),
        steps=steps,
    )


@router.get("/to-point")
async def get_route_to_specific_point(
    lat: float = Query(..., description="User latitude"),
    lon: float = Query(..., description="User longitude"),
    target_id: str = Query(..., description="Target water point ID"),
):
    """
    Get a walking route from the user's location to a specific water point.
    """
    # Get target water point
    async with async_session_factory() as session:
        result = await session.execute(
            text("SELECT id, name, latitude, longitude FROM water_points WHERE id = :id"),
            {"id": target_id},
        )
        row = result.fetchone()

    if not row:
        return {"error": f"Water point {target_id} not found"}

    point_name = row[1]
    point_lat = float(row[2])
    point_lon = float(row[3])

    # Straight line distance
    from sqlalchemy import text as t
    async with async_session_factory() as session:
        result = await session.execute(
            text("""
                SELECT ST_Distance(
                    geometry::geography,
                    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
                ) FROM water_points WHERE id = :id
            """),
            {"lon": lon, "lat": lat, "id": target_id},
        )
        straight_distance = result.scalar()

    # Get OSRM route
    route_data = await fetch_osrm_route(lon, lat, point_lon, point_lat)

    if not route_data:
        walking_time = straight_distance / 1.39
        return {
            "nearest_point_id": target_id,
            "nearest_point_name": point_name,
            "nearest_point_lat": point_lat,
            "nearest_point_lon": point_lon,
            "route_geometry": {
                "type": "LineString",
                "coordinates": [[lon, lat], [point_lon, point_lat]],
            },
            "network_distance_meters": round(straight_distance, 1),
            "straight_line_distance_meters": round(straight_distance, 1),
            "walking_time_seconds": round(walking_time, 1),
            "walking_time_minutes": round(walking_time / 60, 1),
            "steps": [],
        }

    steps, network_distance, walking_time = parse_osrm_route(route_data)
    geometry = route_data.get("geometry", {"type": "LineString", "coordinates": []})

    return {
        "nearest_point_id": target_id,
        "nearest_point_name": point_name,
        "nearest_point_lat": point_lat,
        "nearest_point_lon": point_lon,
        "route_geometry": geometry,
        "network_distance_meters": round(network_distance, 1),
        "straight_line_distance_meters": round(straight_distance, 1),
        "walking_time_seconds": round(walking_time, 1),
        "walking_time_minutes": round(walking_time / 60, 1),
        "steps": [s.model_dump() for s in steps],
    }
