"""Tests for spatial query API endpoints."""

IKEJA = {"lat": 6.6018, "lon": 3.3515}


class TestNearest:
    def test_returns_nearest(self, client):
        r = client.get(f"/api/spatial/nearest?lat={IKEJA['lat']}&lon={IKEJA['lon']}")
        assert r.status_code == 200
        data = r.json()
        assert "name" in data
        assert data["distance_meters"] >= 0

    def test_filter_by_type(self, client):
        r = client.get(f"/api/spatial/nearest?lat={IKEJA['lat']}&lon={IKEJA['lon']}&water_type=tap")
        assert r.status_code == 200
        data = r.json()
        if "error" not in data:
            assert data["water_type"] == "tap"


class TestWithinRadius:
    def test_returns_points(self, client):
        r = client.get(f"/api/spatial/within-radius?lat={IKEJA['lat']}&lon={IKEJA['lon']}&radius_meters=5000")
        assert r.status_code == 200
        data = r.json()
        assert data["type"] == "FeatureCollection"
        assert len(data["features"]) > 0

    def test_larger_radius_returns_more(self, client):
        small = client.get(f"/api/spatial/within-radius?lat={IKEJA['lat']}&lon={IKEJA['lon']}&radius_meters=1000").json()
        large = client.get(f"/api/spatial/within-radius?lat={IKEJA['lat']}&lon={IKEJA['lon']}&radius_meters=10000").json()
        assert len(large["features"]) >= len(small["features"])


class TestAnalysis:
    def test_returns_analysis(self, client):
        r = client.get(f"/api/spatial/analysis?lat={IKEJA['lat']}&lon={IKEJA['lon']}&radius_meters=5000")
        assert r.status_code == 200
        data = r.json()
        assert data["total_points_in_radius"] >= 0
        assert "nearest_point" in data


class TestDensity:
    def test_returns_cells(self, client):
        r = client.get("/api/spatial/density")
        assert r.status_code == 200
        data = r.json()
        assert len(data["cells"]) > 0
