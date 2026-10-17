"""Verify an explicitly configured HTTPS demo; keep credentials out of reports.

The workflow phase writes one labeled synthetic rehearsal to a fresh cloud graph.
It refuses a workspace that already has change history. Other phases are read-only.
"""

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

import httpx

parser = argparse.ArgumentParser()
parser.add_argument("phase", choices=("basics", "workflow", "persistence", "agent"))
parser.add_argument("--base-url", required=True)
parser.add_argument("--credentials", default=".runtime/cloud-login.txt")
parser.add_argument("--report", default="artifacts/cloud-verification.json")
args = parser.parse_args()
base = args.base_url.rstrip("/")
url = urlsplit(base)
if url.scheme != "https" or not url.hostname or url.path or url.query or url.fragment or url.username:
    raise SystemExit("Use an exact HTTPS origin without credentials or a path")
report_path = Path(args.report)
report = json.loads(report_path.read_text()) if report_path.exists() else {}
if report and report.get("base_url") != base:
    raise SystemExit("Report belongs to another deployment")
report.update(base_url=base, verified_at=datetime.now(timezone.utc).isoformat())
private = Path(args.credentials).read_text(encoding="utf-8")


@contextmanager
def client_for(username):
    match = re.search(re.escape(username) + r" \([^)]*\)\s+Password: (\S+)", private)
    if not match:
        raise SystemExit("Expected account is missing from private credential file")
    with httpx.Client(base_url=base, timeout=180, headers={"Origin": base}) as client:
        result = client.post("/api/auth/login", json={"username": username, "password": match[1]})
        result.raise_for_status()
        cookie = result.headers["set-cookie"]
        assert "Secure" in cookie and "HttpOnly" in cookie and "SameSite=strict" in cookie
        client.headers["X-CSRF-Token"] = result.json()["csrf"]
        yield client


def call(client, method, path, body=None):
    result = client.request(method, path, json=body)
    if result.status_code != 200:
        # Server errors may include synthetic evidence, but never print credentials.
        raise RuntimeError(f"{method} {path}: HTTP {result.status_code}: {result.text[:500]}")
    return result.json()


def recap_hash(client):
    recap = call(client, "GET", "/api/recap")
    return hashlib.sha256(json.dumps(recap, sort_keys=True).encode()).hexdigest()


if args.phase == "basics":
    with httpx.Client(base_url=base, timeout=30) as anonymous:
        assert anonymous.get("/").status_code == 200
        assert anonymous.get("/api/healthz").json() == {"status": "ready"}
        assert anonymous.get("/api/overview").status_code == 401
        assert anonymous.get("/api/health").status_code == 401
        assert anonymous.post("/api/auth/login", json={"username": "judge-viewer", "password": "placeholder"}).status_code == 403
        assert anonymous.post("/api/auth/login", json={"username": "judge-viewer", "password": "placeholder"}, headers={"Origin": "https://other.example"}).status_code == 403
    with client_for("judge-viewer") as client:
        assert call(client, "GET", "/api/auth/session")["role"] == "viewer"
        assert call(client, "GET", "/api/health")["database"] == "available"
        assert call(client, "GET", "/api/readiness")["status"] in ("supported", "review_required")
        assert call(client, "GET", "/api/impact/approval-export")["count"] == 7
        assert call(client, "GET", "/api/search?q=Atlas")
        assert client.post("/api/changes/withdraw-security").status_code == 403
        assert client.post("/api/changes/withdraw-security", headers={"X-CSRF-Token": ""}).status_code == 403
    report["https_accounts_origins_csrf_roles_and_graph_reads"] = True

elif args.phase == "workflow":
    with client_for("judge-reviewer") as client:
        assert call(client, "GET", "/api/recap")["changes"] == [], "Workflow verification requires a fresh synthetic graph"
        assert call(client, "GET", "/api/readiness")["status"] == "supported"
        change = call(client, "POST", "/api/changes/withdraw-security", {})
        assert change["created"] and change["impact"]["count"] == 7
        event_id = change["event"]["id"]
        assert change["event"]["recorded_by"] == "judge-reviewer"
        plan = call(client, "POST", "/api/plans", {})
        approved = call(client, "POST", "/api/actions/approve", {"plan_id": plan["id"], "selected": [plan["proposals"][0]["id"]]})
        assert approved["created"] == 1
        task = next(row["action"] for row in approved["actions"] if row["event_id"] == event_id)
        assert task["approved_by"] == "judge-reviewer"
        call(client, "PATCH", "/api/actions/" + task["id"], {"state": "completed"})
        assert call(client, "GET", "/api/readiness")["status"] == "review_required"
        health = call(client, "GET", "/api/health")
        review = call(client, "POST", "/api/restorations", {
            "event_id": event_id,
            "expected_revision": health["revision"],
            "title": "Synthetic cloud deployment verification review",
            "reference": "CLOUD-VERIFY-2026-10-17",
            "excerpt": "Synthetic deployment rehearsal: the export prerequisite was reviewed and explicitly approved for this fictional launch cohort. This is verification data, not a real security review.",
            "synthetic": True,
            "approval_confirmed": True,
        })
        assert review["can_approve"], review["blockers"]
        final = call(client, "POST", "/api/restorations/" + review["review"]["id"] + "/approve", {
            "expected_revision": review["revision"],
            "fingerprint": review["fingerprint"],
            "reviewer_id": "person-1",
            "reviewed_targets": [item["id"] for item in review["impact"]["items"]],
            "note": "Synthetic deployment rehearsal: reviewed all returned affected targets and retained the original evidence history.",
            "confirm": True,
        })
        assert final["review"]["approved_by"] == "judge-reviewer"
        assert call(client, "GET", "/api/readiness")["status"] == "supported"
        report.update(synthetic_workflow_completed=True, withdrawal_impact=7, approved_followups=1, workflow_event_id=event_id, restored_assumption_id=review["candidate"]["id"], recap_sha256_before_restart=recap_hash(client))

elif args.phase == "persistence":
    with client_for("judge-viewer") as client:
        assert recap_hash(client) == report["recap_sha256_before_restart"]
        assert call(client, "GET", "/api/readiness")["status"] == "supported"
        report["records_equal_after_operator_triggered_restart"] = True

else:
    with client_for("judge-viewer") as client:
        assert call(client, "GET", "/api/health")["agent_configured"]
        result = call(client, "POST", "/api/agent", {"question": "Is Project Beacon ready to launch? Use assess_launch_readiness for project-beacon and cite the returned versioned sources and dependency paths.", "project_id": "project-beacon"})
        assert result["trace"] and result["answer"]["source_ids"]
        Path("artifacts/cloud-agent.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        report.update(live_model_tool_loop=True, model_source_ids=result["answer"]["source_ids"], model_tool_calls=len(result["trace"]))

report_path.parent.mkdir(parents=True, exist_ok=True)
report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
