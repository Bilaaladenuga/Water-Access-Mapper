"""
Data export endpoints - download water points as GeoJSON or CSV.
"""

from fastapi import APIRouter, Query
from fastapi.responses import Response
from sqlalchemy import text
import csv
import io
import json

from database import async_session_factory

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/geojson")
async def export_geojson(
    lga: str | None = Query(None, description="Filter by LGA name"),
    water_type: str | None = Query(None, description="Filter by water type"),
    status: str | None = Query(None, description="Filter by status"),
):
    """Export water points as GeoJSON FeatureCollection."""
    async with async_session_factory() as session:
        conditions = []
        params = []
        idx = 1

        if lga:
            conditions.append(f"wp.lga = ${idx}")
            params.append(lga)
            idx += 1
        if water_type:
            conditions.append(f"wp.water_type = ${idx}")
            params.append(water_type)
            idx += 1
        if status:
            conditions.append(f"wp.status = ${idx}")
            params.append(status)
            idx += 1

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query = text(f"""
            SELECT
                wp.id,
                wp.name,
                wp.water_type,
                wp.status,
                wp.source,
                wp.lga,
                wp.latitude,
                wp.longitude,
                wp.verified,
                ST_AsGeoJSON(wp.geometry)::json AS geometry
            FROM water_points wp
            {where_clause}
            ORDER BY wp.id
        """)
        result = await session.execute(query, params)
        rows = result.fetchall()

    features = []
    for row in rows:
        geom = row[9]
        if isinstance(geom, (memoryview, bytes)):
            geom = json.loads(geom.tobytes().decode("utf-8")) if hasattr(geom, "tobytes") else json.loads(bytes(geom).decode("utf-8"))
        features.append({
            "type": "Feature",
            "id": str(row[0]),
            "geometry": geom,
            "properties": {
                "id": str(row[0]),
                "name": row[1],
                "water_type": row[2],
                "status": row[3],
                "source": row[4],
                "lga": row[5],
                "latitude": float(row[6]) if row[6] else None,
                "longitude": float(row[7]) if row[7] else None,
                "verified": row[8],
            },
        })

    geojson = {
        "type": "FeatureCollection",
        "name": "water_access_mapper_points",
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"},
        },
        "features": features,
    }

    content = json.dumps(geojson, indent=2)
    return Response(
        content=content,
        media_type="application/geo+json",
        headers={
            "Content-Disposition": f'attachment; filename="water_points.geojson"'
        },
    )


@router.get("/csv")
async def export_csv(
    lga: str | None = Query(None, description="Filter by LGA name"),
    water_type: str | None = Query(None, description="Filter by water type"),
    status: str | None = Query(None, description="Filter by status"),
):
    """Export water points as CSV."""
    async with async_session_factory() as session:
        conditions = []
        params = []
        idx = 1

        if lga:
            conditions.append(f"wp.lga = ${idx}")
            params.append(lga)
            idx += 1
        if water_type:
            conditions.append(f"wp.water_type = ${idx}")
            params.append(water_type)
            idx += 1
        if status:
            conditions.append(f"wp.status = ${idx}")
            params.append(status)
            idx += 1

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query = text(f"""
            SELECT
                wp.id,
                wp.name,
                wp.water_type,
                wp.status,
                wp.source,
                wp.lga,
                wp.latitude,
                wp.longitude,
                wp.verified,
                wp.created_at,
                wp.updated_at
            FROM water_points wp
            {where_clause}
            ORDER BY wp.id
        """)
        result = await session.execute(query, params)
        rows = result.fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "name", "water_type", "status", "source",
        "lga", "latitude", "longitude", "verified",
        "created_at", "updated_at",
    ])
    for row in rows:
        writer.writerow(row)

    content = output.getvalue()
    return Response(
        content=content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="water_points.csv"'
        },
    )
