"""
Crowdsourcing endpoints (Phase 8 — User Submissions & Reports).

Allows users to:
- Submit new water points (unverified by default)
- Report broken water points
- Report incorrect locations
- List pending submissions and reports

Unverified submissions are stored separately and must be reviewed
before becoming trusted data.
"""

import json
import uuid

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text

from database import async_session_factory

router = APIRouter(prefix="/api/crowd", tags=["crowdsourcing"])


class WaterPointSubmission(BaseModel):
    """Schema for submitting a new water point."""
    name: str = Field(..., min_length=1, max_length=255)
    water_type: str = Field(..., pattern="^(tap|well|borehole|spring|rainwater|other)$")
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    description: str = Field("", max_length=1000)
    submitted_by: str = Field("anonymous", max_length=255)


class ReportSubmission(BaseModel):
    """Schema for reporting an issue with a water point."""
    water_point_id: str
    report_type: str = Field(..., pattern="^(broken|incorrect_location|needs_repair|contaminated|other)$")
    description: str = Field("", max_length=1000)
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    reported_by: str = Field("anonymous", max_length=255)


# ──────────────────────────────────────────────
# 8.1 Submit a new water point
# ──────────────────────────────────────────────
@router.post("/submit")
async def submit_water_point(submission: WaterPointSubmission):
    """
    Submit a new water point for review.

    The point is stored as UNVERIFIED and must be reviewed
    before appearing in the main water_points table.
    """
    submission_id = str(uuid.uuid4())

    try:
        async with async_session_factory() as session:
            sql = text("""
                INSERT INTO water_point_submissions
                (id, name, water_type, description, latitude, longitude,
                 submitted_by, status, created_at)
                VALUES
                (:id, :name, :water_type, :description, :lat, :lon,
                 :submitted_by, 'pending', NOW())
                RETURNING id
            """)
            await session.execute(sql, {
                "id": submission_id,
                "name": submission.name,
                "water_type": submission.water_type,
                "description": submission.description,
                "lat": submission.latitude,
                "lon": submission.longitude,
                "submitted_by": submission.submitted_by,
            })
            await session.commit()

            return {
                "success": True,
                "message": "Water point submitted for review",
                "submission_id": submission_id,
                "status": "pending",
                "note": "Your submission will be reviewed before appearing on the map",
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Submission failed: {str(e)}")


# ──────────────────────────────────────────────
# 8.2 Report an issue with a water point
# ──────────────────────────────────────────────
@router.post("/report")
async def report_water_point(report: ReportSubmission):
    """
    Report an issue with an existing water point.

    Reports are stored in the water_point_reports table
    and flagged for review.
    """
    report_id = str(uuid.uuid4())

    try:
        async with async_session_factory() as session:
            # Validate the water point exists
            result = await session.execute(
                text("SELECT id FROM water_points WHERE id = :id"),
                {"id": report.water_point_id}
            )
            if result.fetchone() is None:
                raise HTTPException(status_code=404, detail="Water point not found")

            # Insert report — generate a UUID for reported_by to match column type
            reporter_id = str(uuid.uuid4())
            sql = text("""
                INSERT INTO water_point_reports
                (id, water_point_id, report_type, description, latitude, longitude,
                 reported_by, resolved, created_at)
                VALUES
                (:id, :water_point_id, :report_type, :description, :lat, :lon,
                 :reported_by, false, NOW())
                RETURNING id
            """)
            await session.execute(sql, {
                "id": report_id,
                "water_point_id": report.water_point_id,
                "report_type": report.report_type,
                "description": report.description,
                "lat": report.latitude,
                "lon": report.longitude,
                "reported_by": reporter_id,
            })
            await session.commit()

            return {
                "success": True,
                "message": f"Report filed: {report.report_type}",
                "report_id": report_id,
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report failed: {str(e)}")


# ──────────────────────────────────────────────
# 8.3 List submissions
# ──────────────────────────────────────────────
@router.get("/submissions")
async def list_submissions(
    status: str = Query("pending", description="Filter: pending, approved, rejected"),
    limit: int = Query(50, ge=1, le=200),
):
    """List submissions filtered by status."""
    if status not in ("pending", "approved", "rejected"):
        raise HTTPException(status_code=400, detail="Invalid status filter")

    try:
        async with async_session_factory() as session:
            sql = text("""
                SELECT id, name, water_type, description, latitude, longitude,
                       submitted_by, status, created_at
                FROM water_point_submissions
                WHERE status = :status
                ORDER BY created_at DESC
                LIMIT :limit
            """)
            result = await session.execute(sql, {"status": status, "limit": limit})
            rows = result.fetchall()

            submissions = []
            for row in rows:
                submissions.append({
                    "id": str(row[0]),
                    "name": row[1],
                    "water_type": row[2],
                    "description": row[3],
                    "latitude": float(row[4]) if row[4] else None,
                    "longitude": float(row[5]) if row[5] else None,
                    "submitted_by": row[6],
                    "status": row[7],
                    "created_at": row[8].isoformat() if row[8] else None,
                })

            return {
                "submissions": submissions,
                "total": len(submissions),
                "status_filter": status,
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


# ──────────────────────────────────────────────
# 8.4 List reports
# ──────────────────────────────────────────────
@router.get("/reports")
async def list_reports(
    resolved: bool = Query(False, description="Filter by resolution status"),
    limit: int = Query(50, ge=1, le=200),
):
    """List water point reports filtered by resolution status."""
    try:
        async with async_session_factory() as session:
            sql = text("""
                SELECT r.id, r.water_point_id, r.report_type, r.description,
                       r.latitude, r.longitude, r.reported_by, r.resolved,
                       r.created_at, w.name as point_name
                FROM water_point_reports r
                LEFT JOIN water_points w ON r.water_point_id = w.id
                WHERE r.resolved = :resolved
                ORDER BY r.created_at DESC
                LIMIT :limit
            """)
            result = await session.execute(sql, {"resolved": resolved, "limit": limit})
            rows = result.fetchall()

            reports = []
            for row in rows:
                reports.append({
                    "id": str(row[0]),
                    "water_point_id": str(row[1]) if row[1] else None,
                    "point_name": row[9],
                    "report_type": row[2],
                    "description": row[3],
                    "latitude": float(row[4]) if row[4] else None,
                    "longitude": float(row[5]) if row[5] else None,
                    "reported_by": row[6],
                    "resolved": row[7],
                    "created_at": row[8].isoformat() if row[8] else None,
                })

            return {
                "reports": reports,
                "total": len(reports),
                "resolved_filter": resolved,
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


# ──────────────────────────────────────────────
# 8.5 Approve a submission (admin)
# ──────────────────────────────────────────────
@router.post("/approve/{submission_id}")
async def approve_submission(submission_id: str):
    """
    Approve a pending submission — inserts it into the main water_points table
    with verified=true.
    """
    try:
        async with async_session_factory() as session:
            # Get the submission
            result = await session.execute(
                text("SELECT id, name, water_type, latitude, longitude FROM water_point_submissions WHERE id = :id AND status = 'pending'"),
                {"id": submission_id}
            )
            row = result.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Submission not found or already processed")

            # Insert into water_points as verified
            new_id = str(uuid.uuid4())
            lat_val = float(row[3])
            lon_val = float(row[4])
            sql = text("""
                INSERT INTO water_points
                (id, name, water_type, status, source, latitude, longitude, geometry,
                 verified, created_at, updated_at)
                VALUES
                (:id, :name, :water_type, 'unknown', 'crowdsourced',
                 :lat, :lon,
                 ST_SetSRID(ST_MakePoint(:lon_geom, :lat_geom), 4326),
                 true, NOW(), NOW())
            """)
            await session.execute(sql, {
                "id": new_id,
                "name": row[1],
                "water_type": row[2],
                "lat": lat_val,
                "lon": lon_val,
                "lat_geom": lat_val,
                "lon_geom": lon_val,
            })

            # Mark submission as approved
            await session.execute(
                text("UPDATE water_point_submissions SET status = 'approved' WHERE id = :id"),
                {"id": submission_id}
            )
            await session.commit()

            return {
                "success": True,
                "message": "Submission approved and added to water_points",
                "new_water_point_id": new_id,
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Approval failed: {str(e)}")


# ──────────────────────────────────────────────
# 8.6 Reject a submission (admin)
# ──────────────────────────────────────────────
@router.post("/reject/{submission_id}")
async def reject_submission(submission_id: str):
    """Reject a pending submission."""
    try:
        async with async_session_factory() as session:
            result = await session.execute(
                text("UPDATE water_point_submissions SET status = 'rejected' WHERE id = :id AND status = 'pending' RETURNING id"),
                {"id": submission_id}
            )
            if result.fetchone() is None:
                raise HTTPException(status_code=404, detail="Submission not found or already processed")
            await session.commit()

            return {"success": True, "message": "Submission rejected"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rejection failed: {str(e)}")


# ──────────────────────────────────────────────
# 8.7 Resolve a report (admin)
# ──────────────────────────────────────────────
@router.post("/resolve/{report_id}")
async def resolve_report(report_id: str):
    """Mark a report as resolved."""
    try:
        async with async_session_factory() as session:
            result = await session.execute(
                text("UPDATE water_point_reports SET resolved = true, resolved_at = NOW() WHERE id = :id AND resolved = false RETURNING id"),
                {"id": report_id}
            )
            if result.fetchone() is None:
                raise HTTPException(status_code=404, detail="Report not found or already resolved")
            await session.commit()

            return {"success": True, "message": "Report resolved"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Resolution failed: {str(e)}")
