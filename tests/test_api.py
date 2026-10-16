import uuid
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
import pytest
from backend.graph import Store
from backend.seed import seed
from backend.service import Continuum
import backend.main as main


@pytest.fixture
def client(monkeypatch):
    store = Store("continuum_api_" + uuid.uuid4().hex)
    seed(store)
    monkeypatch.setattr(main, "store", store)
    monkeypatch.setattr(main, "service", Continuum(store))
    yield TestClient(main.app, base_url="http://127.0.0.1:8000")
    store.graph.delete()


def test_api_full_contract(client):
    assert client.get("/api/overview").status_code == 200
    assert client.get("/api/search?q=Atlas").json()
    assert client.get("/api/entities/project-atlas").json()["ownership"]["conflict"]
    assert client.get("/api/readiness").json()["status"] == "supported"
    assert client.post("/api/changes/withdraw-security").json()["impact"]["count"] == 7
    plan = client.post("/api/plans").json()
    body = {"plan_id": plan["id"], "selected": [plan["proposals"][0]["id"]]}
    assert client.post("/api/actions/approve", json=body).status_code == 200
    assert client.post("/api/actions/approve", json=body).json()["created"] == 0
    assert len(client.get("/api/recap").json()["actions"]) == 1


def test_api_origin_and_validation(client):
    assert (
        client.post(
            "/api/changes/withdraw-security",
            headers={"Origin": "https://untrusted.example"},
        ).status_code
        == 403
    )
    assert client.get("/api/recap").json()["changes"] == []
    assert (
        client.post(
            "/api/actions/approve", json={"plan_id": "bad", "selected": []}
        ).status_code
        == 422
    )
    assert (
        client.post("/api/agent", json={"question": "x", "approve": True}).status_code
        == 422
    )


def test_api_database_outage(monkeypatch):
    monkeypatch.setattr(main, "store", Store("unavailable_api", port=6399))
    response = TestClient(main.app, base_url="http://127.0.0.1:8000").get("/api/health")
    assert response.status_code == 503 and response.json()["dependency"] == "FalkorDB"


def test_concurrent_approval_creates_single_task(client):
    client.post("/api/changes/withdraw-security")
    plan = client.post("/api/plans").json()
    body = {"plan_id": plan["id"], "selected": [plan["proposals"][0]["id"]]}
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(
            pool.map(lambda _: client.post("/api/actions/approve", json=body), range(2))
        )
    assert 200 in [r.status_code for r in responses]
    assert all(r.status_code in (200, 409) for r in responses)
    assert len(client.get("/api/recap").json()["actions"]) == 1


def test_actual_model_endpoint_outage_is_honest(client, monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "llama3:latest")
    monkeypatch.setenv("LLM_API_STYLE", "ollama_json")
    monkeypatch.setenv("LLM_BASE_URL", "http://127.0.0.1:11439")
    response = client.post("/api/agent", json={"question": "Is Project Atlas ready?"})
    assert response.status_code == 503 and response.json()["dependency"] == "model"
    assert client.get("/api/recap").json()["actions"] == []
