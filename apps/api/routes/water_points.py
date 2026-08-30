"""
Water Points API Routes — Water Access Mapper

Provides GeoJSON endpoints for water points and study areas.
"""

import json
from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import text
from database import async_session_factory

router = APIRouter(prefix="/api", tags=["water-points"])


class WaterPointCount(BaseModel):
    total: int
    by_status: dict[str, int]
    by_type: dict[str, int]
    by_source: dict[str, int]


@router.get("/water-points/geojson")
async def get_water_points_geojson(
    status: str | None = Query(None, description="Filter by status"),
    water_type: str | None = Query(None, description="Filter by water type"),
):
    """Get all water points as a GeoJSON FeatureCollection."""
    conditions = []
    params = {}

    if status:
        conditions.append("status = :status")
        params["status"] = status
    if water_type:
        conditions.append("water_type = :water_type")
        params["water_type"] = water_type

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    query = f"""
        SELECT id, name, water_type, status, source,
               latitude, longitude,
               ST_AsGeoJSON(geometry) as geojson
        FROM water_points
        {where_clause}
        ORDER BY name
    """

    async with async_session_factory() as session:
        result = await session.execute(text(query), params)
        rows = result.fetchall()

    features = []
    for row in rows:
        geo = json.loads(row[7])
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
            },
            "geometry": geo,
        })

    return {"type": "FeatureCollection", "features": features}


@router.get("/water-points/stats")
async def get_water_points_stats():
    """Get statistics about water points."""
    async with async_session_factory() as session:
        result = await session.execute(text("SELECT COUNT(*) FROM water_points"))
        total = result.scalar()

        result = await session.execute(text(
            "SELECT status, COUNT(*) FROM water_points GROUP BY status"
        ))
        by_status = {row[0]: row[1] for row in result.fetchall()}

        result = await session.execute(text(
            "SELECT water_type, COUNT(*) FROM water_points GROUP BY water_type"
        ))
        by_type = {row[0]: row[1] for row in result.fetchall()}

        result = await session.execute(text(
            "SELECT source, COUNT(*) FROM water_points GROUP BY source"
        ))
        by_source = {row[0]: row[1] for row in result.fetchall()}

    return WaterPointCount(
        total=total, by_status=by_status, by_type=by_type, by_source=by_source,
    )


@router.get("/study-areas/geojson")
async def get_study_areas_geojson():
    """Get all study areas as a GeoJSON FeatureCollection."""
    async with async_session_factory() as session:
        result = await session.execute(text("""
            SELECT id, name, description, ST_AsGeoJSON(geometry) as geojson
            FROM study_areas ORDER BY name
        """))
        rows = result.fetchall()

    features = []
    for row in rows:
        geo = json.loads(row[3])
        features.append({
            "type": "Feature",
            "id": str(row[0]),
            "properties": {"id": str(row[0]), "name": row[1], "description": row[2]},
            "geometry": geo,
        })

    return {"type": "FeatureCollection", "features": features}
