"""Build a dated summary only from executed hardening verification artifacts."""

from datetime import datetime, timezone
import json
from pathlib import Path
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parents[1]
art = root / "artifacts"
tree = ET.parse(art / "pytest-hardening.xml").getroot()
suites = [tree] if tree.tag == "testsuite" else list(tree)
tests = sum(int(s.get("tests", 0)) for s in suites)
failed = sum(int(s.get("failures", 0)) + int(s.get("errors", 0)) for s in suites)
skipped = sum(int(s.get("skipped", 0)) for s in suites)
assert tests >= 66 and failed == 0 and skipped == 0
python_audit = json.loads(
    (art / "dependency-audit.json").read_text(encoding="utf-8-sig")
)
frontend_audit = json.loads(
    (art / "frontend-dependency-audit.json").read_text(encoding="utf-8-sig")
)
python_findings = sum(len(d["vulns"]) for d in python_audit["dependencies"])
frontend_findings = frontend_audit["metadata"]["vulnerabilities"]["total"]
assert not python_findings and not frontend_findings
browser = json.loads((art / "browser-hardening.json").read_text())
assert len(browser["scenarios"]) == 2
assert all(
    s["state_unchanged"]
    and s["mobile_no_overflow"]
    and not s["page_errors"]
    and not s["csp_violations"]
    for s in browser["scenarios"]
)
runtime = json.loads((art / "hardening-runtime.json").read_text())
assert (
    runtime["before"] == runtime["after"]
    and runtime["existing_history_and_actions_preserved"]
)
agent = json.loads((art / "live-agent.json").read_text())
assert len(agent["runs"]) == 2 and all(r["status"] == "passed" for r in agent["runs"])
report = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "product": "CONTINUUM",
    "team": "OmegaRuby",
    "scope": "First local-demo hardening pass",
    "tests": {
        "passed": tests,
        "failed": failed,
        "skipped": skipped,
        "duration_seconds": sum(float(s.get("time", 0)) for s in suites),
        "raw_result": "artifacts/pytest-hardening.xml",
    },
    "dependency_audits": {
        "python_known_findings": python_findings,
        "frontend_known_findings": frontend_findings,
        "caveat": "Dated advisory inventories; not proof of security",
    },
    "browser": browser,
    "state_preservation": runtime,
    "live_agent_runs": [
        {
            "scenario": r["scenario"],
            "status": r["status"],
            "elapsed_ms": r["elapsed_ms"],
            "tools": [t["tool"] for t in r["result"]["trace"]],
        }
        for r in agent["runs"]
    ],
    "remaining_limits": [
        "Local only; no public authentication/authorization or tenant isolation",
        "Curated metadata; natural-language entailment unverified",
        "Per-document guarded imports; whole-fixture seeding is multiwrite",
        "Unmanaged database races unsupported",
        "Process-local single model slot",
        "Bounded traversal and retrieval; no enterprise load benchmark",
        "Security restoration workflow not implemented",
        "Full Docker execution and clean install on another machine unverified",
    ],
}
(art / "hardening-verification.json").write_text(
    json.dumps(report, indent=2), encoding="utf-8"
)
print(
    json.dumps(
        {
            "tests": report["tests"],
            "dependency_audits": report["dependency_audits"],
            "state_preserved": True,
        },
        indent=2,
    )
)
