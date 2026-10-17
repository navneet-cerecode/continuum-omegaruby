"""Public-host guards and cloud credentials, without provisioning paid services."""

import json
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.trustedhost import TrustedHostMiddleware
from backend.hosting import configuration
from backend.access import accounts
from test_release import secured, PASSWORD
import backend.main as main


def cloud_env(monkeypatch):
    monkeypatch.setenv("CONTINUUM_ENV", "cloud")
    monkeypatch.setenv(
        "CONTINUUM_PUBLIC_ORIGIN", "https://continuum-test.up.railway.app"
    )
    monkeypatch.setenv("CONTINUUM_ACCESS", "accounts")
    monkeypatch.setenv("CONTINUUM_COOKIE_SECURE", "true")


@pytest.mark.parametrize(
    "origin",
    [
        "http://demo.example",
        "https://*.example",
        "https://user:password@demo.example",
        "https://demo.example/path",
        "https://demo.example?key=value",
        "https://demo.example#fragment",
        "",
    ],
)
def test_cloud_refuses_unsafe_origins(monkeypatch, origin):
    cloud_env(monkeypatch)
    monkeypatch.delenv("RAILWAY_PUBLIC_DOMAIN", raising=False)
    monkeypatch.setenv("CONTINUUM_PUBLIC_ORIGIN", origin)
    with pytest.raises(RuntimeError):
        configuration()


def test_cloud_refuses_demo_or_insecure_cookies(monkeypatch):
    cloud_env(monkeypatch)
    monkeypatch.setenv("CONTINUUM_ACCESS", "demo")
    with pytest.raises(RuntimeError, match="account access"):
        configuration()
    monkeypatch.setenv("CONTINUUM_ACCESS", "accounts")
    monkeypatch.setenv("CONTINUUM_COOKIE_SECURE", "false")
    with pytest.raises(RuntimeError, match="Secure"):
        configuration()


def test_cloud_exact_host_and_railway_origin(monkeypatch):
    cloud_env(monkeypatch)
    monkeypatch.delenv("CONTINUUM_PUBLIC_ORIGIN")
    monkeypatch.setenv("RAILWAY_PUBLIC_DOMAIN", "continuum-test.up.railway.app")
    cfg = configuration()
    assert cfg.origins == {"https://continuum-test.up.railway.app"}
    app = FastAPI()
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=cfg.hosts)

    @app.get("/")
    def root():
        return {"ok": True}

    client = TestClient(app, base_url=cfg.origin)
    assert client.get("/").status_code == 200
    assert client.get("/", headers={"Host": "healthcheck.railway.app"}).status_code == 200
    assert client.get("/", headers={"Host": "other.up.railway.app"}).status_code == 400


def test_cloud_login_requires_exact_origin_and_sets_secure_cookie(secured, monkeypatch):
    cloud_env(monkeypatch)
    monkeypatch.setattr(main, "hosting", configuration())
    client = TestClient(main.app, base_url="https://127.0.0.1:8000")
    assert client.get("/api/healthz").json() == {"status": "ready"}
    assert client.get("/api/overview").status_code == 401
    body = {"username": "admin", "password": PASSWORD}
    assert client.post("/api/auth/login", json=body).status_code == 403
    assert (
        client.post(
            "/api/auth/login", json=body, headers={"Origin": "https://attacker.example"}
        ).status_code
        == 403
    )
    response = client.post(
        "/api/auth/login", json=body, headers={"Origin": main.hosting.origin}
    )
    assert response.status_code == 200 and "Secure" in response.headers["set-cookie"]
    assert client.get("/api/overview").status_code == 200
    assert (
        client.post(
            "/api/changes/withdraw-security", headers={"Origin": main.hosting.origin}
        ).status_code
        == 403
    )


def test_accounts_can_load_secret_environment_and_fail_closed(secured, monkeypatch):
    _, _, path = secured
    expected = json.loads(path.read_text(encoding="utf-8"))
    monkeypatch.setenv("CONTINUUM_ACCOUNTS_JSON", json.dumps(expected))
    monkeypatch.setenv("CONTINUUM_ACCOUNTS_FILE", "missing-file.json")
    assert accounts() == expected
    monkeypatch.setenv("CONTINUUM_ACCOUNTS_JSON", "invalid")
    client = TestClient(main.app, base_url="http://127.0.0.1:8000")
    assert client.get("/api/healthz").status_code == 503


def test_database_tls_verifies_host_and_credentials_stay_server_side(monkeypatch):
    import backend.graph as graph

    captured = {}

    class FakeDB:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def select_graph(self, name):
            return self

        def ro_query(self, *args, **kwargs):
            class Result:
                header = []
                result_set = []

            return Result()

    monkeypatch.setattr(graph, "FalkorDB", FakeDB)
    monkeypatch.setenv("FALKORDB_TLS", "true")
    monkeypatch.setenv("FALKORDB_PASSWORD", "test-only-database-password")
    graph.Store("tls-test").query("RETURN 1")
    assert (
        captured["ssl"]
        and captured["ssl_check_hostname"]
        and captured["ssl_cert_reqs"] == "required"
    )
    assert captured["password"] == "test-only-database-password"
    monkeypatch.setenv("FALKORDB_TLS", "typo")
    with pytest.raises(ValueError, match="FALKORDB_TLS"):
        graph.Store("tls-test").query("RETURN 1")
