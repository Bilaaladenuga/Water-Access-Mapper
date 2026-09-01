"""Tests for water points and study areas API."""


class TestWaterPoints:
    def test_geojson_returns_feature_collection(self, client):
        r = client.get("/api/water-points/geojson")
        assert r.status_code == 200
        data = r.json()
        assert data["type"] == "FeatureCollection"
        assert len(data["features"]) > 0

    def test_feature_has_required_properties(self, client):
        r = client.get("/api/water-points/geojson")
        props = r.json()["features"][0]["properties"]
        assert "id" in props
        assert "name" in props
        assert "water_type" in props
        assert "status" in props
        assert "source" in props

    def test_feature_has_valid_geometry(self, client):
        r = client.get("/api/water-points/geojson")
        geom = r.json()["features"][0]["geometry"]
        assert geom["type"] == "Point"
        lon, lat = geom["coordinates"]
        assert 2.0 <= lon <= 5.0
        assert 6.0 <= lat <= 7.0

    def test_filter_by_status(self, client):
        r = client.get("/api/water-points/geojson?status=operational")
        assert r.status_code == 200
        for f in r.json()["features"]:
            assert f["properties"]["status"] == "operational"

    def test_filter_by_type(self, client):
        r = client.get("/api/water-points/geojson?water_type=tap")
        assert r.status_code == 200
        for f in r.json()["features"]:
            assert f["properties"]["water_type"] == "tap"


class TestStats:
    def test_returns_stats(self, client):
        r = client.get("/api/water-points/stats")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] > 0
        assert sum(data["by_status"].values()) == data["total"]

    def test_has_all_sources(self, client):
        data = client.get("/api/water-points/stats").json()
        assert "osm" in data["by_source"]
        assert "sample" in data["by_source"]


class TestStudyAreas:
    def test_returns_lagos(self, client):
        r = client.get("/api/study-areas/geojson")
        assert r.status_code == 200
        names = [f["properties"]["name"] for f in r.json()["features"]]
        assert "Lagos State" in names
