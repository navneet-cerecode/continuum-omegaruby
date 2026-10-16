"""Real project-scoped HTTP/Ollama verification on the owned browser QA graph."""

from datetime import datetime, timezone
import json
from pathlib import Path
from time import perf_counter
import httpx

root = Path(__file__).resolve().parents[1]
graph = (root / ".runtime/lifecycle-qa-graph.txt").read_text().strip()
assert graph.startswith("continuum_lifecycle_")
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
    before = client.get("/api/overview").json()
    assert len(before["history"]) == 3 and all(
        item["event"]["state"] == "resolved" for item in before["history"]
    )
    for slug in ("beacon", "orbit"):
        project = "project-" + slug
        question = (
            "Are we ready to launch Project "
            + slug.capitalize()
            + ", and what supports that answer?"
        )
        started = perf_counter()
        response = client.post(
            "/api/agent", json={"project_id": project, "question": question}
        )
        response.raise_for_status()
        result = response.json()
        assert any(
            item["tool"] == "assess_launch_readiness"
            and item["input"].get("value") == project
            for item in result["trace"]
        )
        assert result["answer"]["conclusion"].startswith(
            "Recorded prerequisites support"
        )
        assert any(
            id.startswith("doc-approval-restoration-")
            for id in result["answer"]["source_ids"]
        )
        assert all(path[0] == project for path in result["answer"]["supporting_paths"])
        run = {
            "project": project,
            "scenario": "restored-readiness",
            "status": "passed",
            "elapsed_ms": round((perf_counter() - started) * 1000, 3),
            "result": result,
        }
        report["runs"].append(run)
        print(
            json.dumps(
                {
                    "project": project,
                    "elapsed_ms": run["elapsed_ms"],
                    "answer": result["answer"],
                    "tools": [x["tool"] for x in result["trace"]],
                }
            ),
            flush=True,
        )
    assert client.get("/api/overview").json() == before
    report["state_unchanged"] = True
(root / "artifacts/live-multi-project.json").write_text(
    json.dumps(report, indent=2), encoding="utf-8"
)
