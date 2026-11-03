"""Integration tests for FastAPI endpoints."""
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200

def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "neo4j_connected" in data
    assert "neo4j_uri_configured" in data

def test_upload_requires_zip():
    response = client.post(
        "/api/v1/upload",
        data={"name": "test_repo"},
        files={"file": ("test.txt", b"plain text content", "text/plain")}
    )
    assert response.status_code == 400
    assert "zip" in response.json()["detail"].lower()

def test_upload_requires_name():
    response = client.post(
        "/api/v1/upload",
        data={"name": ""},
        files={"file": ("test.zip", b"dummy zip", "application/zip")}
    )
    assert response.status_code in (400, 422)
