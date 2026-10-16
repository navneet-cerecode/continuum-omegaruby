"""Real, credential-free installed model run against isolated real FalkorDB."""

import json
from pathlib import Path
import sys
from time import perf_counter
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.graph import Store
from backend.seed import seed
from backend.service import Continuum
from backend.agent import run_agent

if __name__ == "__main__":
    s = Store("continuum_live_" + uuid.uuid4().hex)
    seed(s)
    svc = Continuum(s)
    report = {"provider": "Local Ollama", "live": True, "runs": []}
    try:
        for label, question in [
            (
                "before",
                "Are we ready to launch Project Atlas, and what supports that answer?",
            ),
            (
                "after",
                "What changed, why was the launch flagged, and what remains unresolved?",
            ),
        ]:
            if label == "after":
                svc.withdraw()
                plan = svc.propose()
                svc.approve(plan["id"], [plan["proposals"][0]["id"]])
            start = perf_counter()
            try:
                result = run_agent(
                    svc,
                    question,
                    observer=lambda entry: print(
                        json.dumps(
                            {
                                "tool": entry["tool"],
                                "input": entry["input"],
                                "error": entry["result"].get("error")
                                if isinstance(entry["result"], dict)
                                else None,
                            }
                        ),
                        flush=True,
                    ),
                )
                assert result["answer"]["source_ids"], (
                    "Live answer must cite actual sources"
                )
                assert result["answer"]["supporting_paths"], (
                    "Live answer must expose complete returned paths"
                )
                if label == "before":
                    assert "not ready" not in result["answer"]["conclusion"].lower(), (
                        "Readiness conclusion contradicted supported prerequisites"
                    )
                item = {
                    "scenario": label,
                    "question": question,
                    "elapsed_ms": round((perf_counter() - start) * 1000, 3),
                    "status": "passed",
                    "result": result,
                }
                report["runs"].append(item)
                print(
                    json.dumps(
                        {
                            "scenario": label,
                            "elapsed_ms": item["elapsed_ms"],
                            "answer": result["answer"],
                            "tools": [x["tool"] for x in result["trace"]],
                        }
                    ),
                    flush=True,
                )
            except Exception as exc:
                report["runs"].append(
                    {
                        "scenario": label,
                        "status": "failed",
                        "error": str(exc),
                        "trace": getattr(exc, "trace", []),
                        "elapsed_ms": round((perf_counter() - start) * 1000, 3),
                    }
                )
                print(json.dumps(report["runs"][-1]), flush=True)
                raise
    finally:
        Path("artifacts/live-agent.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        s.graph.delete()
