import threading
from concurrent.futures import ThreadPoolExecutor
from test_api import client
import backend.main as main


def test_host_rebinding_guard(client):
    response = client.get("/api/health", headers={"Host": "attacker.example"})
    assert response.status_code == 400
    assert client.get("/api/health").status_code == 200


def test_body_limit_and_json_boundary(client):
    revision = client.get("/api/health").json()["revision"]
    assert (
        client.post(
            "/api/changes/withdraw-security",
            content="x" * 32769,
            headers={"Content-Type": "application/json"},
        ).status_code
        == 413
    )
    assert (
        client.post(
            "/api/changes/withdraw-security",
            content="{}",
            headers={"Content-Type": "text/plain"},
        ).status_code
        == 415
    )
    assert (
        client.post(
            "/api/changes/withdraw-security",
            content="{}",
            headers={"Content-Type": "application/json", "Content-Encoding": "gzip"},
        ).status_code
        == 415
    )
    assert client.get("/api/health").json()["revision"] == revision


def test_cross_site_request_without_origin_refused(client):
    assert (
        client.post(
            "/api/changes/withdraw-security", headers={"Sec-Fetch-Site": "cross-site"}
        ).status_code
        == 403
    )
    assert client.get("/api/recap").json()["changes"] == []


def test_safe_security_headers_and_range_bounds(client):
    response = client.get("/")
    assert response.headers["x-content-type-options"] == "nosniff"
    policy = response.headers["content-security-policy"]
    assert "script-src 'self'" in policy and "frame-ancestors 'none'" in policy
    assert "unsafe-eval" not in policy
    assert (
        client.get(
            "/", headers={"Range": "bytes=" + ",".join("0-1" for _ in range(18))}
        ).status_code
        == 400
    )


def test_concurrent_model_requests_are_bounded(client, monkeypatch):
    started = threading.Event()
    finish = threading.Event()

    def model(*args):
        started.set()
        assert finish.wait(5)
        return {"conclusion": "simulated for concurrency test"}

    monkeypatch.setattr(main, "run_agent", model)
    with ThreadPoolExecutor(max_workers=1) as pool:
        first = pool.submit(
            client.post, "/api/agent", json={"question": "Investigate Atlas"}
        )
        assert started.wait(3)
        try:
            assert (
                client.post(
                    "/api/agent", json={"question": "Investigate Atlas again"}
                ).status_code
                == 429
            )
        finally:
            finish.set()
        assert first.result().status_code == 200
    assert (
        client.post(
            "/api/agent", json={"question": "Inspect Atlas once more"}
        ).status_code
        == 200
    )
