"""
Spatial Query API Routes — Water Access Mapper

Provides PostGIS-powered spatial analysis endpoints:
- Nearest water point (KNN)
- Water points within radius (ST_DWithin)
- Water point density analysis
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import text
from database import async_session_factory

router = APIRouter(prefix="/api/spatial", tags=["spatial-queries"])


class NearestPointResponse(BaseModel):
    id: str
    name: str
    water_type: str
    status: str
    source: str
    latitude: float
    longitude: float
    distance_meters: float


class RadiusResult(BaseModel):
    type: str
    name: str
    water_type: str
    status: str
    source: str
    latitude: float
    longitude: float
    distance_meters: float


class DensityCell(BaseModel):
    grid_x: float
    grid_y: float
    count: int


class SpatialAnalysisResponse(BaseModel):
    total_points_in_radius: int
    operational_in_radius: int
    broken_in_radius: int
    nearest_point: NearestPointResponse | None
    average_distance: float


# ──────────────────────────────────────────────
# 5.1 Nearest Water Point (KNN)
# ──────────────────────────────────────────────
@router.get("/nearest")
async def get_nearest_water_point(
    lat: float = Query(..., description="User latitude"),
    lon: float = Query(..., description="User longitude"),
    water_type: str | None = Query(None, description="Filter by water type"),
    status: str | None = Query(None, description="Filter by status"),
):
    """
    Find the nearest water point to a given location using K-Nearest Neighbor.

    Uses PostGIS KNN operator (<->) for efficient spatial indexing.
    """
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

    # <-> is the KNN distance operator — uses spatial index for fast lookup
    query = f"""
        SELECT id, name, water_type, status, source,
               latitude, longitude,
               ST_Distance(
                   geometry::geography,
                   ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
               ) AS distance_meters
        FROM water_points
        {where_clause}
        ORDER BY geometry <-> ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)
        LIMIT 1
    """

    async with async_session_factory() as session:
        result = await session.execute(text(query), params)
        row = result.fetchone()

    if not row:
        return {"error": "No water points found matching criteria"}

    return NearestPointResponse(
        id=str(row[0]),
        name=row[1],
        water_type=row[2],
        status=row[3],
        source=row[4],
        latitude=float(row[5]),
        longitude=float(row[6]),
        distance_meters=round(float(row[7]), 1),
    )


# ──────────────────────────────────────────────
# 5.2 Water Points Within Radius
# ──────────────────────────────────────────────
@router.get("/within-radius")
async def get_water_points_within_radius(
    lat: float = Query(..., description="Center latitude"),
    lon: float = Query(..., description="Center longitude"),
    radius_meters: float = Query(1000, description="Search radius in meters"),
    water_type: str | None = Query(None, description="Filter by water type"),
    status: str | None = Query(None, description="Filter by status"),
):
    """
    Find all water points within a given radius.

    Uses PostGIS ST_DWithin for efficient circular search using geography type
    (calculates true geodesic distance on the Earth's surface).
    """
    conditions = []
    params: dict = {"lon": lon, "lat": lat, "radius": radius_meters}

    if water_type:
        conditions.append("water_type = :water_type")
        params["water_type"] = water_type
    if status:
        conditions.append("status = :status")
        params["status"] = status

    extra_where = ""
    if conditions:
        extra_where = "AND " + " AND ".join(conditions)

    # ST_DWithin with geography type uses meters for distance
    query = f"""
        SELECT id, name, water_type, status, source,
               latitude, longitude,
               ST_Distance(
                   geometry::geography,
                   ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
               ) AS distance_meters
        FROM water_points
        WHERE ST_DWithin(
            geometry::geography,
            ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
            :radius
        )
        {extra_where}
        ORDER BY distance_meters
    """

    async with async_session_factory() as session:
        result = await session.execute(text(query), params)
        rows = result.fetchall()

    features = []
    for row in rows:
        features.append({
            "type": "Feature",
            "id": str(row[0]),
            "properties": {
                "id": str(row[0]),
                "name": row[1],
                "water_type": row[2],
                "status": row[3],
                "source": row[4],
                "latitude": float(row[5]),
                "longitude": float(row[6]),
                "distance_meters": round(float(row[7]), 1),
            },
        })

    return {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "center": {"lat": lat, "lon": lon},
            "radius_meters": radius_meters,
            "count": len(features),
        },
    }


# ──────────────────────────────────────────────
# 5.3 & 5.4 Combined Spatial Analysis
# ──────────────────────────────────────────────
@router.get("/analysis")
async def spatial_analysis(
    lat: float = Query(..., description="Center latitude"),
    lon: float = Query(..., description="Center longitude"),
    radius_meters: float = Query(1000, description="Analysis radius in meters"),
):
    """
    Combined spatial analysis within a radius:
    - Total points
    - Operational/broken counts
    - Nearest point
    - Average distance
    """
    params: dict = {"lon": lon, "lat": lat, "radius": radius_meters}

    # Count by status within radius
    count_query = """
        SELECT
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE status = 'operational') as operational,
            COUNT(*) FILTER (WHERE status = 'broken') as broken,
            COUNT(*) FILTER (WHERE status = 'unknown') as unknown,
            AVG(ST_Distance(
                geometry::geography,
                ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
            )) as avg_distance
        FROM water_points
        WHERE ST_DWithin(
            geometry::geography,
            ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
            :radius
        )
    """

    # Nearest point
    nearest_query = """
        SELECT id, name, water_type, status, source,
               latitude, longitude,
               ST_Distance(
                   geometry::geography,
                   ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
               ) AS distance_meters
        FROM water_points
        ORDER BY geometry <-> ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)
        LIMIT 1
    """

    async with async_session_factory() as session:
        count_result = await session.execute(text(count_query), params)
        counts = count_result.fetchone()

        nearest_result = await session.execute(text(nearest_query), params)
        nearest = nearest_result.fetchone()

    nearest_point = None
    if nearest:
        nearest_point = NearestPointResponse(
            id=str(nearest[0]),
            name=nearest[1],
            water_type=nearest[2],
            status=nearest[3],
            source=nearest[4],
            latitude=float(nearest[5]),
            longitude=float(nearest[6]),
            distance_meters=round(float(nearest[7]), 1),
        )

    return SpatialAnalysisResponse(
        total_points_in_radius=counts[0],
        operational_in_radius=counts[1],
        broken_in_radius=counts[2],
        nearest_point=nearest_point,
        average_distance=round(float(counts[4]), 1) if counts[4] else 0,
    )


# ──────────────────────────────────────────────
# 5.5 Water Point Density Analysis
# ──────────────────────────────────────────────
@router.get("/density")
async def get_water_point_density(
    grid_size: float = Query(0.01, description="Grid cell size in degrees (~1km)"),
):
    """
    Calculate water point density using a grid overlay.

    Divides the study area into grid cells and counts water points per cell.
    Useful for identifying underserved areas (cells with 0 or 1 points).
    """
    query = """
        SELECT
            ROUND(CAST(ST_X(geometry) AS NUMERIC), 2) AS grid_x,
            ROUND(CAST(ST_Y(geometry) AS NUMERIC), 2) AS grid_y,
            COUNT(*) AS point_count
        FROM water_points
        GROUP BY
            ROUND(CAST(ST_X(geometry) AS NUMERIC), 2),
            ROUND(CAST(ST_Y(geometry) AS NUMERIC), 2)
        ORDER BY point_count DESC
    """

    async with async_session_factory() as session:
        result = await session.execute(text(query))
        rows = result.fetchall()

    cells = []
    total_points = 0
    max_density = 0

    for row in rows:
        count = row[2]
        total_points += count
        max_density = max(max_density, count)
        cells.append({
            "grid_x": float(row[0]),
            "grid_y": float(row[1]),
            "count": count,
        })

    return {
        "cells": cells,
        "metadata": {
            "total_points": total_points,
            "total_cells": len(cells),
            "max_density": max_density,
            "grid_size_degrees": grid_size,
            "average_per_cell": round(total_points / len(cells), 1) if cells else 0,
        },
    }
