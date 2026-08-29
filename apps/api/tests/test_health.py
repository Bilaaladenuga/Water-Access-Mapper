"""
Tests for the /health endpoint.
"""

from fastapi.testclient import TestClient
from main import app


client = TestClient(app)


def test_health_endpoint():
    """Test that health endpoint returns correct response."""
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "water-access-mapper-api"
    assert "version" in data
    assert "timestamp" in data


def test_root_endpoint():
    """Test that root endpoint returns API info."""
    response = client.get("/")
    assert response.status_code == 200

    data = response.json()
    assert data["name"] == "Water Access Mapper API"
    assert "docs" in data
    assert "health" in data
