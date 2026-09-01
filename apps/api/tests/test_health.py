"""Tests for health and root endpoints."""


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "healthy"
    assert data["service"] == "water-access-mapper-api"


def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Water Access Mapper API"
    assert "docs" in data
