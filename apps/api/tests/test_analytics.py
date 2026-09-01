"""Tests for analytics API endpoints."""


class TestSummary:
    def test_returns_summary(self, client):
        r = client.get("/api/analytics/summary")
        assert r.status_code == 200
        data = r.json()
        assert data["total_water_points"] > 0
        assert 0 <= data["operational_rate"] <= 100

    def test_counts_add_up(self, client):
        data = client.get("/api/analytics/summary").json()
        assert sum(data["by_status"].values()) == data["total_water_points"]


class TestBreakdown:
    def test_returns_charts(self, client):
        r = client.get("/api/analytics/breakdown")
        assert r.status_code == 200
        data = r.json()
        assert len(data["status_chart"]) > 0
        assert len(data["type_chart"]) > 0

    def test_chart_items(self, client):
        item = client.get("/api/analytics/breakdown").json()["status_chart"][0]
        assert "label" in item
        assert "value" in item


class TestCoverage:
    def test_returns_coverage(self, client):
        r = client.get("/api/analytics/coverage")
        assert r.status_code == 200
        data = r.json()
        assert 3000 <= data["study_area_km2"] <= 5000
        assert data["density_per_km2"] > 0


class TestDataQuality:
    def test_returns_quality(self, client):
        r = client.get("/api/analytics/data-quality")
        assert r.status_code == 200
        data = r.json()
        assert 0 <= data["quality_score"] <= 100

    def test_counts_add_up(self, client):
        data = client.get("/api/analytics/data-quality").json()
        assert data["named_points"] + data["unnamed_points"] == data["total_points"]
