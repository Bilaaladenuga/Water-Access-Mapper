"""
Water Access Mapper — FastAPI Backend

A geospatial API for managing water point data,
powered by FastAPI and PostGIS.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime

app = FastAPI(
    title="Water Access Mapper API",
    description="Geospatial API for water point management and analysis",
    version="0.1.0",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
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


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Water Access Mapper API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }
