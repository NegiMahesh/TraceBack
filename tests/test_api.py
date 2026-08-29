"""Integration tests for TraceBack API endpoints."""

import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


class TestHealthEndpoints:
    def test_root(self):
        r = client.get("/")
        assert r.status_code == 200
        assert r.json()["name"] == "TraceBack"

    def test_health(self):
        r = client.get("/api/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_system_status(self):
        r = client.get("/api/system/status")
        assert r.status_code == 200
        data = r.json()
        assert "ollama" in data
        assert "model" in data


class TestCrashEndpoints:
    def test_analyze_valid_traceback(self):
        tb = """Traceback (most recent call last):
  File "test.py", line 5, in <module>
    x = 1 / 0
ZeroDivisionError: division by zero"""

        r = client.post("/api/crash/analyze", json={
            "traceback_text": tb,
        })
        assert r.status_code == 200
        data = r.json()
        assert data["parsed"]["error_type"] == "ZeroDivisionError"

    def test_analyze_empty(self):
        r = client.post("/api/crash/analyze", json={
            "traceback_text": "",
        })
        assert r.status_code == 400

    def test_analyze_non_traceback(self):
        r = client.post("/api/crash/analyze", json={
            "traceback_text": "This is just regular text",
        })
        assert r.status_code == 400


class TestRepositoryEndpoints:
    def test_get_repository(self):
        r = client.get("/api/repository")
        assert r.status_code in [200, 404]  # depends on default path

    def test_get_files(self):
        r = client.get("/api/repository/files")
        assert r.status_code in [200, 404]


class TestInvestigationEndpoints:
    def test_list_investigations(self):
        r = client.get("/api/investigations")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_get_nonexistent_investigation(self):
        r = client.get("/api/investigations/nonexistent")
        assert r.status_code == 404
