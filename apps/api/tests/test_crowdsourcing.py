"""Tests for crowdsourcing API endpoints."""


class TestSubmit:
    def test_submit_new_point(self, client):
        r = client.post("/api/crowd/submit", json={
            "name": "Test Well", "water_type": "well",
            "latitude": 6.5, "longitude": 3.4,
            "description": "test", "submitted_by": "tester",
        })
        assert r.status_code == 200
        assert r.json()["success"] is True
        assert r.json()["status"] == "pending"

    def test_requires_name(self, client):
        r = client.post("/api/crowd/submit", json={
            "name": "", "water_type": "well", "latitude": 6.5, "longitude": 3.4,
        })
        assert r.status_code == 422


class TestReport:
    def test_report_existing_point(self, client):
        wp = client.get("/api/water-points/geojson").json()["features"][0]["properties"]
        r = client.post("/api/crowd/report", json={
            "water_point_id": wp["id"], "report_type": "broken",
            "description": "test", "reported_by": "tester",
        })
        assert r.status_code == 200
        assert r.json()["success"] is True

    def test_report_nonexistent(self, client):
        r = client.post("/api/crowd/report", json={
            "water_point_id": "00000000-0000-0000-0000-000000000000",
            "report_type": "broken",
        })
        assert r.status_code == 404


class TestListEndpoints:
    def test_list_submissions(self, client):
        r = client.get("/api/crowd/submissions?status=pending")
        assert r.status_code == 200
        assert "submissions" in r.json()

    def test_list_reports(self, client):
        r = client.get("/api/crowd/reports?resolved=false")
        assert r.status_code == 200
        assert "reports" in r.json()

    def test_invalid_status(self, client):
        r = client.get("/api/crowd/submissions?status=invalid")
        assert r.status_code == 400
