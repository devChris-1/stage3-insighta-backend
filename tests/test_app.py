import pytest
from app import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_profiles_requires_auth(client):
    resp = client.get("/api/profiles", headers={"X-API-Version": "1"})
    assert resp.status_code == 401

def test_profiles_requires_version_header(client):
    resp = client.get("/api/profiles")
    assert resp.status_code == 400

def test_search_requires_auth(client):
    resp = client.get("/api/profiles/search?q=young males", headers={"X-API-Version": "1"})
    assert resp.status_code == 401
