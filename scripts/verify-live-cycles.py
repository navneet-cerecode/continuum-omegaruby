"""Actual Ollama distinguishes an old resolved incident from a new withdrawal."""

from datetime import datetime, timezone
import json
from pathlib import Path
from time import perf_counter
import httpx

root = Path(__file__).resolve().parents[1]
graph = (root / ".runtime/lifecycle-qa-graph.txt").read_text().strip()
browser = json.loads((root / "artifacts/browser-cycles.json").read_text())
assert graph == browser["graph"]
first = browser["events"][0]
report = {
    "verified_at": datetime.now(timezone.utc).isoformat(),
    "graph": graph,
    "live": True,
    "provider": "Local Ollama",
    "runs": [],
}
with httpx.Client(base_url="http://127.0.0.1:8000", timeout=120) as client:
    assert (
        client.get("/api/entities/lifecycle-qa-marker").json()["entity"]["name"]
        == graph
    )
    view = client.get("/api/overview", params={"project_id": "project-atlas"}).json()
    assert len(view["project_history"]) == 2 and view["context"]["can_withdraw"]
    response = client.post(
        "/api/changes/withdraw",
        json={
            "project_id": "project-atlas",
            "prerequisite_id": view["context"]["prerequisite_id"],
            "expected_revision": view["revision"],
            "reason": "Synthetic third-cycle withdrawal to verify that earlier resolution does not establish current approval.",
        },
    )
    response.raise_for_status()
    third = response.json()["event"]["id"]
    report["setup_third_event_id"] = third
    before = client.get("/api/overview").json()
    for scenario, body in [
        (
            "historical-incident",
            {
                "project_id": "project-atlas",
                "event_id": first,
                "question": "Use get_change_event to inspect the selected incident. Explain whether this older resolved incident means the current prerequisite is approved.",
            },
        ),
        (
            "current-readiness",
            {
                "project_id": "project-atlas",
                "question": "Are we ready to launch Project Atlas now, and what supports that answer?",
            },
        ),
    ]:
        started = perf_counter()
        response = client.post("/api/agent", json=body)
        response.raise_for_status()
        result = response.json()
        if scenario == "historical-incident":
            assert any(
                t["tool"] == "get_change_event" and t["input"].get("value") == first
                for t in result["trace"]
            )
            assert (
                "selected incident is resolved" in result["answer"]["conclusion"]
                and "review_required" in result["answer"]["conclusion"]
            )
            assert any(
                path[-1] == "approval-export"
                for path in result["answer"]["supporting_paths"]
            )
        else:
            assert (
                result["answer"]["conclusion"]
                == "Review required; launch is not automatically cancelled."
            )
        run = {
            "scenario": scenario,
            "status": "passed",
            "elapsed_ms": round((perf_counter() - started) * 1000, 3),
            "result": result,
        }
        report["runs"].append(run)
        print(
            json.dumps(
                {
                    "scenario": scenario,
                    "elapsed_ms": run["elapsed_ms"],
                    "answer": result["answer"],
                    "tools": [t["tool"] for t in result["trace"]],
                }
            ),
            flush=True,
        )
    assert client.get("/api/overview").json() == before
    assert (
        client.get("/api/entities/" + third).json()["entity"]["state"] == "unresolved"
    )
    report["model_state_unchanged"] = True
(root / "artifacts/live-cycles.json").write_text(
    json.dumps(report, indent=2), encoding="utf-8"
)
