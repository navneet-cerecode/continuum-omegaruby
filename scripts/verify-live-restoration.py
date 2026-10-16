"""Actual HTTP → local Ollama → real restored graph; no mocked model responses."""

from datetime import datetime, timezone
import json
from pathlib import Path
from time import perf_counter
import httpx

ROOT = Path(__file__).resolve().parents[1]
graph = (ROOT / ".runtime/lifecycle-qa-graph.txt").read_text().strip()
assert graph.startswith("continuum_lifecycle_")
report = {
    "verified_at": datetime.now(timezone.utc).isoformat(),
    "live": True,
    "graph": graph,
    "provider": "Local Ollama",
    "runs": [],
}
with httpx.Client(base_url="http://127.0.0.1:8000", timeout=120) as client:
    marker = client.get("/api/entities/lifecycle-qa-marker").json()
    assert marker["entity"]["name"] == graph
    before = client.get("/api/overview").json()
    assert before["history"][0]["event"]["state"] == "resolved"
    for scenario, question in [
        (
            "restored-readiness",
            "Are we ready to launch Project Atlas, and what supports that answer?",
        ),
        (
            "resolved-recap",
            "What changed, how was the security withdrawal resolved, and what remains unresolved?",
        ),
    ]:
        started = perf_counter()
        response = client.post("/api/agent", json={"question": question})
        response.raise_for_status()
        result = response.json()
        assert result["answer"]["supporting_paths"]
        assert any(
            id.startswith("doc-security-restoration-")
            for id in result["answer"]["source_ids"]
        )
        if scenario == "restored-readiness":
            assert result["answer"]["conclusion"].startswith(
                "Recorded prerequisites support"
            )
        else:
            assert "withdrawal was resolved" in result["answer"]["conclusion"]
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
                    "conclusion": result["answer"]["conclusion"],
                    "tools": [t["tool"] for t in result["trace"]],
                    "elapsed_ms": run["elapsed_ms"],
                }
            ),
            flush=True,
        )
    after = client.get("/api/overview").json()
    assert before == after
    report["state_unchanged"] = True
(ROOT / "artifacts/live-restoration.json").write_text(
    json.dumps(report, indent=2), encoding="utf-8"
)
