"""
LGA-level analytics endpoints - water access breakdown by Local Government Area.
"""

from fastapi import APIRouter, Query
from sqlalchemy import text
from database import async_session_factory

router = APIRouter(prefix="/api/lga", tags=["lga"])


@router.get("/analytics")
async def lga_analytics():
    """
    Water access analytics for each of Lagos's 20 LGAs.
    Uses PostGIS spatial joins to count water points per LGA boundary.
    """
    async with async_session_factory() as session:
        # Main query: count water points per LGA using spatial join
        query = text("""
            SELECT
                l.name AS lga_name,
                l.area_sqkm,
                l.center_lat,
                l.center_lon,
                COUNT(wp.id) AS total_points,
                COUNT(wp.id) FILTER (WHERE wp.status = 'operational' AND NOT wp.status_estimated) AS operational,
                COUNT(wp.id) FILTER (WHERE wp.status = 'broken' AND NOT wp.status_estimated) AS broken,
                COUNT(wp.id) FILTER (WHERE wp.status = 'unknown') AS unknown_status,
                COUNT(wp.id) FILTER (WHERE wp.status = 'operational' AND wp.status_estimated) AS operational_estimated,
                COUNT(wp.id) FILTER (WHERE wp.status = 'broken' AND wp.status_estimated) AS broken_estimated,
                COUNT(wp.id) FILTER (WHERE wp.water_type = 'tap') AS taps,
                COUNT(wp.id) FILTER (WHERE wp.water_type = 'well') AS wells,
                COUNT(wp.id) FILTER (WHERE wp.water_type = 'borehole') AS boreholes,
                COUNT(wp.id) FILTER (WHERE wp.water_type = 'spring') AS springs,
                COUNT(wp.id) FILTER (WHERE wp.water_type = 'waterworks') AS waterworks,
                COUNT(wp.id) FILTER (WHERE wp.source = 'osm') AS osm_points,
                COUNT(wp.id) FILTER (WHERE wp.source = 'sample') AS sample_points,
                COUNT(wp.id) FILTER (WHERE wp.source = 'crowdsourced') AS crowdsourced_points,
                COUNT(wp.id) FILTER (WHERE wp.source = 'grid') AS grid_points
            FROM lga_boundaries l
            LEFT JOIN water_points wp ON ST_Contains(l.geometry, wp.geometry)
            GROUP BY l.name, l.area_sqkm, l.center_lat, l.center_lon
            ORDER BY total_points DESC
        """)
        result = await session.execute(query)
        rows = result.fetchall()

        # Points outside every LGA polygon (coastal/offshore or borderline
        # coordinates). Surfaced so per-LGA totals reconcile with the map total.
        grand_total = await session.scalar(text("SELECT COUNT(*) FROM water_points"))
        unassigned = grand_total - sum(row[4] for row in rows)

    lgas = []
    for row in rows:
        total = row[4]
        area = row[1] or 1
        density = round(total / area, 2) if area > 0 else 0
        operational = row[5]
        broken = row[6]
        operational_estimated = row[8]
        broken_estimated = row[9]
        # Rate only over points whose status is actually recorded. GRID points
        # carry no status, so dividing by `total` would report ~0% everywhere.
        # Modelled (status_estimated) points are excluded and reported as their
        # own rate — a 72% assumption is not a survey result.
        assessed = operational + broken
        operational_rate = round((operational / assessed * 100), 1) if assessed > 0 else 0
        estimated_assessed = operational_estimated + broken_estimated
        estimated_operational_rate = (
            round((operational_estimated / estimated_assessed * 100), 1)
            if estimated_assessed > 0 else 0
        )

        lgas.append({
            "lga_name": row[0],
            "area_km2": round(area, 2),
            "center_lat": row[2],
            "center_lon": row[3],
            "total_points": total,
            "operational": operational,
            "broken": broken,
            "unknown_status": row[7],
            "operational_estimated": operational_estimated,
            "broken_estimated": broken_estimated,
            "status_estimated": estimated_assessed,
            "status_assessed": assessed,
            "density_per_km2": density,
            "operational_rate_pct": operational_rate,
            "estimated_operational_rate_pct": estimated_operational_rate,
            "taps": row[10],
            "wells": row[11],
            "boreholes": row[12],
            "springs": row[13],
            "waterworks": row[14],
            "osm_points": row[15],
            "sample_points": row[16],
            "crowdsourced_points": row[17],
            "grid_points": row[18],
        })

    return {
        "total_lgas": len(lgas),
        "total_points": sum(l["total_points"] for l in lgas),
        "unassigned_points": unassigned,
        "grand_total": grand_total,
        "lgas": lgas,
    }


@router.get("/summary")
async def lga_summary():
    """Quick summary stats across all LGAs."""
    async with async_session_factory() as session:
        query = text("""
            SELECT
                COUNT(DISTINCT l.name) AS total_lgas,
                COUNT(wp.id) AS total_points,
                ROUND(AVG(CASE WHEN sub.total > 0 THEN sub.total END)::numeric, 1) AS avg_points_per_lga,
                MIN(CASE WHEN sub.total > 0 THEN sub.total END) AS min_points_lga,
                MAX(sub.total) AS max_points_lga
            FROM lga_boundaries l
            LEFT JOIN water_points wp ON ST_Contains(l.geometry, wp.geometry)
            LEFT JOIN (
                SELECT wp2.lga, COUNT(*) AS total
                FROM water_points wp2
                GROUP BY wp2.lga
            ) sub ON sub.lga = l.name
        """)
        result = await session.execute(query)
        row = result.fetchone()

        # LGAs with 0 points
        query_empty = text("""
            SELECT l.name
            FROM lga_boundaries l
            LEFT JOIN water_points wp ON ST_Contains(l.geometry, wp.geometry)
            WHERE wp.id IS NULL
        """)
        empty_result = await session.execute(query_empty)
        empty_lgas = [r[0] for r in empty_result.fetchall()]

    return {
        "total_lgas": row[0],
        "total_points": row[1],
        "avg_points_per_lga": float(row[2]) if row[2] else 0,
        "min_points": row[3],
        "max_points": row[4],
        "lgas_with_no_data": empty_lgas,
    }


@router.get("/boundaries")
async def lga_boundaries_geojson():
    """Return all LGA boundaries as GeoJSON for map display."""
    async with async_session_factory() as session:
        query = text("""
            SELECT
                l.name,
                l.area_sqkm,
                l.center_lat,
                l.center_lon,
                COUNT(wp.id) AS total_points,
                ST_AsGeoJSON(l.geometry)::json AS geometry
            FROM lga_boundaries l
            LEFT JOIN water_points wp ON ST_Contains(l.geometry, wp.geometry)
            GROUP BY l.name, l.area_sqkm, l.center_lat, l.center_lon, l.geometry
            ORDER BY l.name
        """)
        result = await session.execute(query)
        rows = result.fetchall()

    features = []
    for row in rows:
        features.append({
            "type": "Feature",
            "geometry": row[5],
            "properties": {
                "name": row[0],
                "area_km2": round(row[1], 2),
                "center_lat": row[2],
                "center_lon": row[3],
                "total_points": row[4],
            },
        })

    return {
        "type": "FeatureCollection",
        "features": features,
    }
