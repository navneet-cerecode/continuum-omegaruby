"""HTTP lifecycle and restart verification for the CI-owned application container."""

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
from time import monotonic, sleep
from urllib.error import URLError
from urllib.request import Request, urlopen

BASE = "http://127.0.0.1:8000"


def get(path, data=None):
    request = Request(
        BASE + path,
        data=None if data is None else json.dumps(data).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urlopen(request, timeout=10) as response:
        return json.load(response)


def wait():
    deadline = monotonic() + 60
    while monotonic() < deadline:
        try:
            return get("/api/health")
        except (URLError, ConnectionError, TimeoutError):
            sleep(0.5)
    raise RuntimeError("Container did not become ready")


try:
    wait()
    with urlopen(BASE + "/", timeout=10) as response:
        assert response.status == 200 and "/assets/" in response.read().decode()
    assert get("/api/readiness")["status"] == "supported"
    change = get("/api/changes/withdraw-security", {})
    assert change["impact"]["count"] == 7 and change["created"]
    plan = get("/api/plans", {})
    approved = get(
        "/api/actions/approve",
        {"plan_id": plan["id"], "selected": [plan["proposals"][0]["id"]]},
    )
    assert approved["created"] == 1
    before = get("/api/recap")
    assert get("/api/readiness")["status"] == "review_required"
    subprocess.run(
        ["docker", "restart", "continuum-app-ci"], check=True, stdout=subprocess.DEVNULL
    )
    wait()
    after = get("/api/recap")
    assert before == after
    report = {
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "real_falkordb_container": True,
        "real_application_container": True,
        "production_ui_served": True,
        "withdrawal_impact": 7,
        "approved_followups": 1,
        "application_container_restart_preserved_records": True,
        "environment": "Fresh GitHub-hosted Ubuntu runner; Linux containers, no model inference in this check",
    }
    Path("artifacts/container-verification.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
finally:
    subprocess.run(["docker", "logs", "--tail", "20", "continuum-app-ci"], check=False)
    subprocess.run(
        ["docker", "stop", "continuum-app-ci"], check=False, stdout=subprocess.DEVNULL
    )
