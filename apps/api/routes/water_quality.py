"""
Water Quality API Routes — Water Access Mapper

Provides endpoints for water quality data:
- Get quality data for a specific water point
- Get quality summary across all tested points
- Submit new quality test results
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text

from database import async_session_factory

router = APIRouter(prefix="/api/water-quality", tags=["water-quality"])


class QualityTest(BaseModel):
    """Schema for submitting a water quality test."""
    water_point_id: str
    ph: float = Field(..., ge=0, le=14)
    turbidity: float = Field(..., ge=0)
    coliform_count: int = Field(..., ge=0)
    conductivity: float = Field(0, ge=0)
    temperature: float = Field(25, ge=0, le=100)
    notes: str = ""
    tested_by: str = "anonymous"


@router.get("/point/{water_point_id}")
async def get_quality_for_point(water_point_id: str):
    """Get all quality test results for a specific water point."""
    async with async_session_factory() as session:
        result = await session.execute(
            text("""
                SELECT id, test_date, ph, turbidity, coliform_count,
                       conductivity, temperature, status, notes, tested_by
                FROM water_quality
                WHERE water_point_id = :wp_id
                ORDER BY test_date DESC
            """),
            {"wp_id": water_point_id}
        )
        rows = result.fetchall()

    if not rows:
        return {"quality": [], "count": 0}

    quality = []
    for row in rows:
        quality.append({
            "id": str(row[0]),
            "test_date": row[1].isoformat() if row[1] else None,
            "ph": float(row[2]) if row[2] else None,
            "turbidity": float(row[3]) if row[3] else None,
            "coliform_count": row[4],
            "conductivity": float(row[5]) if row[5] else None,
            "temperature": float(row[6]) if row[6] else None,
            "status": row[7],
            "notes": row[8],
            "tested_by": row[9],
        })

    return {"quality": quality, "count": len(quality)}


@router.get("/summary")
async def get_quality_summary():
    """Get water quality summary statistics."""
    async with async_session_factory() as session:
        # Total tested points
        result = await session.execute(
            text("SELECT COUNT(DISTINCT water_point_id) FROM water_quality")
        )
        total_tested = result.scalar()

        # By status
        result = await session.execute(
            text("SELECT status, COUNT(*) FROM water_quality GROUP BY status ORDER BY status")
        )
        by_status = {row[0]: row[1] for row in result.fetchall()}

        # Average metrics
        result = await session.execute(text("""
            SELECT
                AVG(ph) as avg_ph,
                AVG(turbidity) as avg_turbidity,
                AVG(coliform_count) as avg_coliform,
                AVG(temperature) as avg_temp
            FROM water_quality
        """))
        avgs = result.fetchone()

        # Latest test per point
        result = await session.execute(text("""
            SELECT wq.water_point_id, wq.test_date, wq.status, wq.ph,
                   wp.name, wp.latitude, wp.longitude
            FROM water_quality wq
            JOIN water_points wp ON wq.water_point_id = wp.id
            WHERE wq.id IN (
                SELECT id FROM water_quality
                WHERE water_point_id = wq.water_point_id
                ORDER BY test_date DESC LIMIT 1
            )
            ORDER BY wq.test_date DESC
        """))
        latest = []
        for row in result.fetchall():
            latest.append({
                "water_point_id": str(row[0]),
                "test_date": row[1].isoformat() if row[1] else None,
                "status": row[2],
                "ph": float(row[3]) if row[3] else None,
                "point_name": row[4],
                "latitude": float(row[5]) if row[5] else None,
                "longitude": float(row[6]) if row[6] else None,
            })

    return {
        "total_tested_points": total_tested,
        "by_status": by_status,
        "averages": {
            "ph": round(float(avgs[0]), 1) if avgs[0] else None,
            "turbidity": round(float(avgs[1]), 1) if avgs[1] else None,
            "coliform_count": round(float(avgs[2]), 0) if avgs[2] else None,
            "temperature": round(float(avgs[3]), 1) if avgs[3] else None,
        },
        "latest_results": latest,
    }


@router.get("/geojson")
async def get_quality_geojson():
    """Get all tested water points with their latest quality status as GeoJSON."""
    async with async_session_factory() as session:
        result = await session.execute(text("""
            SELECT DISTINCT ON (wq.water_point_id)
                wq.water_point_id, wq.ph, wq.turbidity, wq.coliform_count,
                wq.status as quality_status, wq.test_date,
                wp.name, wp.water_type, wp.latitude, wp.longitude,
                ST_AsGeoJSON(wp.geometry) as geojson
            FROM water_quality wq
            JOIN water_points wp ON wq.water_point_id = wp.id
            ORDER BY wq.water_point_id, wq.test_date DESC
        """))
        rows = result.fetchall()

    features = []
    for row in rows:
        features.append({
            "type": "Feature",
            "id": str(row[0]),
            "properties": {
                "id": str(row[0]),
                "name": row[6],
                "water_type": row[7],
                "ph": float(row[1]) if row[1] else None,
                "turbidity": float(row[2]) if row[2] else None,
                "coliform_count": row[3],
                "quality_status": row[4],
                "test_date": row[5].isoformat() if row[5] else None,
            },
            "geometry": {
                "type": "Point",
                "coordinates": [float(row[8]), float(row[9])],
            },
        })

    return {"type": "FeatureCollection", "features": features}


@router.post("/submit")
async def submit_quality_test(test: QualityTest):
    """Submit a new water quality test result."""
    async with async_session_factory() as session:
        # Validate water point exists
        result = await session.execute(
            text("SELECT id FROM water_points WHERE id = :id"),
            {"id": test.water_point_id}
        )
        if result.fetchone() is None:
            raise HTTPException(status_code=404, detail="Water point not found")

        # Determine status based on WHO guidelines
        if test.ph < 6.5 or test.ph > 8.5 or test.coliform_count > 100 or test.turbidity > 10:
            status = "poor"
        elif test.ph < 7.0 or test.ph > 8.0 or test.coliform_count > 50 or test.turbidity > 5:
            status = "moderate"
        else:
            status = "good"

        result = await session.execute(
            text("""
                INSERT INTO water_quality
                (water_point_id, ph, turbidity, coliform_count,
                 conductivity, temperature, status, notes, tested_by)
                VALUES
                (:wp_id, :ph, :turbidity, :coliform,
                 :conductivity, :temp, :status, :notes, :tested_by)
                RETURNING id
            """),
            {
                "wp_id": test.water_point_id,
                "ph": test.ph,
                "turbidity": test.turbidity,
                "coliform": test.coliform_count,
                "conductivity": test.conductivity,
                "temp": test.temperature,
                "status": status,
                "notes": test.notes,
                "tested_by": test.tested_by,
            }
        )
        await session.commit()
        row = result.fetchone()

        return {
            "success": True,
            "test_id": str(row[0]),
            "status": status,
            "message": f"Quality test submitted — rated as {status}",
        }
