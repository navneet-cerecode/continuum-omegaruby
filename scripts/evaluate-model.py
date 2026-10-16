"""Small repeatable live local-model evaluation; reports failures, never fabricates passes."""

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from time import perf_counter
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.agent import run_agent, AgentUnavailable  # noqa: E402
from backend.graph import Store  # noqa: E402
from backend.seed import seed  # noqa: E402
from backend.service import Continuum  # noqa: E402

s = Store("continuum_eval_" + uuid.uuid4().hex)
report = {
    "verified_at": datetime.now(timezone.utc).isoformat(),
    "graph": s.name,
    "real_database": True,
    "live_model": True,
    "runs": [],
}
try:
    seed(s)
    service = Continuum(s)
    cases = [
        ("atlas-supported", "project-atlas", False),
        ("beacon-supported", "project-beacon", False),
        ("orbit-supported", "project-orbit", False),
        ("atlas-withdrawn", "project-atlas", True),
        ("beacon-after-atlas-change", "project-beacon", False),
    ]
    for name, project, withdraw in cases:
        if withdraw:
            service.withdraw()
        before = {
            "revision": s.revision(),
            "actions": s.actions(),
            "history": s.history(),
        }
        expected = service.readiness(project)["conclusion"]
        start = perf_counter()
        row = {"scenario": name, "project": project, "expected_conclusion": expected}
        try:
            result = run_agent(
                service,
                "Selected project ID: "
                + project
                + ". Use assess_launch_readiness for this exact project. Are its recorded prerequisites sufficient now? Cite the actual approval and dependency evidence, not just ownership.",
            )
            row.update(
                result=result, elapsed_ms=round((perf_counter() - start) * 1000, 3)
            )
            selected = any(
                t["tool"] == "assess_launch_readiness"
                and t["input"].get("value") == project
                for t in result["trace"]
            )
            row["status"] = (
                "passed"
                if selected
                and result["answer"]["conclusion"] == expected
                and result["citation_check"]["source_excerpts"]
                and not result["citation_check"]["unavailable_path_source_ids"]
                else "failed"
            )
            row["model_citation_coverage_complete"] = result["citation_check"][
                "model_citation_coverage_complete"
            ]
        except AgentUnavailable as exc:
            row.update(
                status="rejected",
                error=str(exc),
                trace=exc.trace,
                elapsed_ms=round((perf_counter() - start) * 1000, 3),
            )
        after = {
            "revision": s.revision(),
            "actions": s.actions(),
            "history": s.history(),
        }
        assert before == after
        row["state_unchanged"] = True
        report["runs"].append(row)
        print(
            json.dumps(
                {
                    k: v
                    for k, v in row.items()
                    if k
                    in (
                        "scenario",
                        "status",
                        "elapsed_ms",
                        "model_citation_coverage_complete",
                        "error",
                    )
                }
            ),
            flush=True,
        )
    report["passed"] = sum(r["status"] == "passed" for r in report["runs"])
    report["model_citation_coverage_complete"] = sum(
        r.get("model_citation_coverage_complete", False) for r in report["runs"]
    )
    report["semantic_entailment"] = (
        "Not established. Source/path coverage and authoritative conclusions are checked; free prose requires human review."
    )
finally:
    if s.graph is not None:
        s.graph.delete()
    report["owned_graph_cleaned"] = True
    (ROOT / "artifacts/release-model-eval.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
