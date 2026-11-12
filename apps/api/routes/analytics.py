"""
Analytics endpoints (Phase 9 — Dashboard Statistics).

Provides comprehensive statistics for the analytics dashboard:
- Summary statistics (total, operational, broken, etc.)
- Breakdown by type, status, source
- Accessibility statistics
- Underserved area analysis
- Data quality metrics
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import text

from database import async_session_factory

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


# ──────────────────────────────────────────────
# 9.1 Summary Statistics
# ──────────────────────────────────────────────
@router.get("/summary")
async def get_summary():
    """
    Get overall summary statistics for the dashboard.
    """
    async with async_session_factory() as session:
        # Total water points
        result = await session.execute(text("SELECT COUNT(*) FROM water_points"))
        total = result.scalar()

        # By status
        result = await session.execute(
            text("SELECT status, COUNT(*) FROM water_points GROUP BY status ORDER BY status")
        )
        by_status = {row[0]: row[1] for row in result.fetchall()}

        # By type
        result = await session.execute(
            text("SELECT water_type, COUNT(*) FROM water_points GROUP BY water_type ORDER BY COUNT(*) DESC")
        )
        by_type = {row[0]: row[1] for row in result.fetchall()}

        # By source
        result = await session.execute(
            text("SELECT source, COUNT(*) FROM water_points GROUP BY source ORDER BY source")
        )
        by_source = {row[0]: row[1] for row in result.fetchall()}

        # Operational rate.
        # Most GRID/OSM points carry no status field, so dividing by the full
        # count would report ~5% and imply almost everything is broken. Report
        # the rate over points whose status is actually known, and expose that
        # denominator so the UI can label it honestly.
        #
        # Two rates are reported separately. GRID statuses are modelled from an
        # assumption (scripts/estimate_grid_status.py) and flagged
        # status_estimated = TRUE; mixing them into one rate would present a
        # guess as a survey result.
        result = await session.execute(text("""
            SELECT
                COUNT(*) FILTER (WHERE status = 'operational' AND NOT status_estimated) AS operational,
                COUNT(*) FILTER (WHERE status = 'broken' AND NOT status_estimated) AS broken,
                COUNT(*) FILTER (WHERE status = 'operational' AND status_estimated) AS estimated_operational,
                COUNT(*) FILTER (WHERE status = 'broken' AND status_estimated) AS estimated_broken,
                COUNT(*) FILTER (WHERE status_estimated) AS estimated_total
            FROM water_points
        """))
        split = result.fetchone()
        operational = split[0]
        broken = split[1]
        estimated_operational = split[2]
        estimated_broken = split[3]
        status_estimated = split[4]
        assessed = operational + broken
        estimated_assessed = estimated_operational + estimated_broken
        unknown = by_status.get("unknown", 0)
        operational_rate = round((operational / assessed * 100), 1) if assessed > 0 else 0
        estimated_operational_rate = (
            round((estimated_operational / estimated_assessed * 100), 1)
            if estimated_assessed > 0 else 0
        )

        # Pending submissions
        result = await session.execute(
            text("SELECT COUNT(*) FROM water_point_submissions WHERE status = 'pending'")
        )
        pending_submissions = result.scalar()

        # Unresolved reports
        result = await session.execute(
            text("SELECT COUNT(*) FROM water_point_reports WHERE resolved = false")
        )
        unresolved_reports = result.scalar()

    return {
        "total_water_points": total,
        "by_status": by_status,
        "by_type": by_type,
        "by_source": by_source,
        "operational_rate": operational_rate,
        "operational_recorded": operational,
        "broken_recorded": broken,
        "status_assessed": assessed,
        "status_unknown": unknown,
        "status_estimated": status_estimated,
        "estimated_assessed": estimated_assessed,
        "estimated_operational": estimated_operational,
        "estimated_broken": estimated_broken,
        "estimated_operational_rate": estimated_operational_rate,
        "pending_submissions": pending_submissions,
        "unresolved_reports": unresolved_reports,
    }


# ──────────────────────────────────────────────
# 9.2 Detailed Breakdown
# ──────────────────────────────────────────────
@router.get("/breakdown")
async def get_breakdown():
    """
    Get detailed breakdown for charts and visualizations.
    """
    async with async_session_factory() as session:
        # Status breakdown for pie chart
        result = await session.execute(text("""
            SELECT status, COUNT(*) as count
            FROM water_points
            GROUP BY status
            ORDER BY count DESC
        """))
        status_chart = [{"label": row[0], "value": row[1]} for row in result.fetchall()]

        # Same breakdown, split by whether the status was recorded in the
        # source dataset or modelled (status_estimated = TRUE).
        result = await session.execute(text("""
            SELECT status, status_estimated, COUNT(*) as count
            FROM water_points
            GROUP BY status, status_estimated
        """))
        status_chart_recorded = []
        status_chart_estimated = []
        for status, is_estimated, count in result.fetchall():
            (status_chart_estimated if is_estimated else status_chart_recorded).append(
                {"label": status, "value": count}
            )
        status_chart_recorded.sort(key=lambda d: d["value"], reverse=True)
        status_chart_estimated.sort(key=lambda d: d["value"], reverse=True)

        # Type breakdown for bar chart
        result = await session.execute(text("""
            SELECT water_type, COUNT(*) as count
            FROM water_points
            GROUP BY water_type
            ORDER BY count DESC
        """))
        type_chart = [{"label": row[0], "value": row[1]} for row in result.fetchall()]

        # Source breakdown for pie chart
        result = await session.execute(text("""
            SELECT source, COUNT(*) as count
            FROM water_points
            GROUP BY source
            ORDER BY count DESC
        """))
        source_chart = [{"label": row[0], "value": row[1]} for row in result.fetchall()]

        # Type by status (stacked bar chart data)
        result = await session.execute(text("""
            SELECT water_type, status, COUNT(*) as count
            FROM water_points
            GROUP BY water_type, status
            ORDER BY water_type, status
        """))
        type_status_data = {}
        for row in result.fetchall():
            wt = row[0]
            status = row[1]
            count = row[2]
            if wt not in type_status_data:
                type_status_data[wt] = {}
            type_status_data[wt][status] = count

        return {
            "status_chart": status_chart,
            "status_chart_recorded": status_chart_recorded,
            "status_chart_estimated": status_chart_estimated,
            "type_chart": type_chart,
            "source_chart": source_chart,
            "type_status_data": type_status_data,
        }


# ──────────────────────────────────────────────
# 9.3 Coverage Analysis
# ──────────────────────────────────────────────
@router.get("/coverage")
async def get_coverage_analysis():
    """
    Analyze water point coverage across Lagos State.
    """
    async with async_session_factory() as session:
        # Study area bounds
        result = await session.execute(text("""
            SELECT ST_XMin(geometry), ST_YMin(geometry),
                   ST_XMax(geometry), ST_YMax(geometry),
                   ST_Area(geometry::geography) / 1e6 as area_km2
            FROM study_areas LIMIT 1
        """))
        bounds = result.fetchone()

        if not bounds:
            return {"error": "No study area defined"}

        west, south, east, north, area_km2 = (
            float(bounds[0]), float(bounds[1]),
            float(bounds[2]), float(bounds[3]),
            float(bounds[4])
        )

        # Points per km2
        result = await session.execute(text("SELECT COUNT(*) FROM water_points"))
        total = result.scalar()
        density = round(total / area_km2, 4) if area_km2 > 0 else 0

        # Nearest-neighbour distance for every point, in one pass.
        # Bucketing per point is O(n) and adds up to the point total, which is
        # meaningful; bucketing point *pairs* is O(n²) and unreadable at this
        # scale (≈900k pairs dominated by the "beyond 2km" bucket).
        result = await session.execute(text("""
            WITH nn AS (
                SELECT wp1.id,
                       (SELECT ST_Distance(wp1.geometry::geography, wp2.geometry::geography)
                        FROM water_points wp2
                        WHERE wp2.id <> wp1.id
                        ORDER BY wp1.geometry <-> wp2.geometry
                        LIMIT 1) AS dist
                FROM water_points wp1
            )
            SELECT
                AVG(dist) AS avg_nearest,
                MIN(dist) AS min_nearest,
                MAX(dist) AS max_nearest,
                COUNT(*) FILTER (WHERE dist <= 500) AS within_500m,
                COUNT(*) FILTER (WHERE dist > 500 AND dist <= 1000) AS between_500m_1km,
                COUNT(*) FILTER (WHERE dist > 1000 AND dist <= 2000) AS between_1km_2km,
                COUNT(*) FILTER (WHERE dist > 2000) AS beyond_2km
            FROM nn
        """))
        nn = result.fetchone()

        return {
            "study_area_km2": round(area_km2, 1),
            "total_points": total,
            "density_per_km2": density,
            "average_nearest_neighbor_m": round(float(nn[0]), 1) if nn and nn[0] else 0,
            "min_nearest_neighbor_m": round(float(nn[1]), 1) if nn and nn[1] else 0,
            "max_nearest_neighbor_m": round(float(nn[2]), 1) if nn and nn[2] else 0,
            "nearest_neighbor_distribution": {
                "within_500m": nn[3] if nn else 0,
                "between_500m_1km": nn[4] if nn else 0,
                "between_1km_2km": nn[5] if nn else 0,
                "beyond_2km": nn[6] if nn else 0,
            },
        }


# ──────────────────────────────────────────────
# 9.4 Data Quality Metrics
# ──────────────────────────────────────────────
@router.get("/data-quality")
async def get_data_quality():
    """
    Assess data quality across the dataset.
    """
    async with async_session_factory() as session:
        # Points with names vs unnamed
        result = await session.execute(text("""
            SELECT
                COUNT(*) FILTER (WHERE name LIKE 'OSM Water Point%' OR name LIKE 'Sample%') as unnamed,
                COUNT(*) FILTER (WHERE name NOT LIKE 'OSM Water Point%' AND name NOT LIKE 'Sample%') as named
            FROM water_points
        """))
        naming = result.fetchone()

        # Points with valid coordinates (within Lagos bounds)
        result = await session.execute(text("""
            SELECT COUNT(*) FROM water_points
            WHERE latitude BETWEEN 6.37 AND 6.70
            AND longitude BETWEEN 2.70 AND 4.35
        """))
        valid_coords = result.scalar()

        result = await session.execute(text("SELECT COUNT(*) FROM water_points"))
        total = result.scalar()

        # Points by verification status
        result = await session.execute(text("""
            SELECT
                COUNT(*) FILTER (WHERE verified = true) as verified,
                COUNT(*) FILTER (WHERE verified = false OR verified IS NULL) as unverified
            FROM water_points
        """))
        verification = result.fetchone()

        return {
            "total_points": total,
            "named_points": naming[1] if naming else 0,
            "unnamed_points": naming[0] if naming else 0,
            "valid_coordinates": valid_coords,
            "invalid_coordinates": total - valid_coords if total and valid_coords else 0,
            "verified_points": verification[0] if verification else 0,
            "unverified_points": verification[1] if verification else 0,
            "quality_score": round(
                ((naming[1] / total * 30) + (valid_coords / total * 40) + (verification[0] / total * 30))
                if total > 0 else 0, 1
            ),
        }
