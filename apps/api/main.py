"""
Water Access Mapper — FastAPI Backend

A geospatial API for managing water point data,
powered by FastAPI and PostGIS.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
from config import get_cors_origins

app = FastAPI(
    title="Water Access Mapper API",
    description="Geospatial API for water point management and analysis",
    version="0.1.0",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    timestamp: str


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.

    Returns service status, version, and current timestamp.
    """
    return HealthResponse(
        status="healthy",
        service="water-access-mapper-api",
        version="0.1.0",
        timestamp=datetime.utcnow().isoformat(),
    )


class DatabaseStatus(BaseModel):
    status: str
    postgresql_version: str | None = None
    postgis_version: str | None = None
    error: str | None = None


@app.get("/database", response_model=DatabaseStatus)
async def database_status():
    """
    Check database connection and PostGIS availability.

    Returns PostgreSQL version and PostGIS version if connected.
    """
    from database import check_db_connection
    result = await check_db_connection()
    return DatabaseStatus(**result)


# Include API routes
from routes.water_points import router as water_points_router
from routes.spatial_queries import router as spatial_router
app.include_router(water_points_router)
app.include_router(spatial_router)


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Water Access Mapper API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
        "database": "/database",
        "water_points": "/api/water-points/geojson",
        "study_areas": "/api/study-areas/geojson",
        "spatial": {
            "nearest": "/api/spatial/nearest?lat=6.5&lon=3.4",
            "within_radius": "/api/spatial/within-radius?lat=6.5&lon=3.4&radius_meters=1000",
            "analysis": "/api/spatial/analysis?lat=6.5&lon=3.4&radius_meters=1000",
            "density": "/api/spatial/density",
        },
    }
