"""Summarize only executed cross-project evidence."""

from datetime import datetime, timezone
import json
from pathlib import Path
import xml.etree.ElementTree as ET

art = Path(__file__).resolve().parents[1] / "artifacts"
tree = ET.parse(art / "pytest-multi-project.xml").getroot()
suites = [tree] if tree.tag == "testsuite" else list(tree)
count = sum(int(s.get("tests", 0)) for s in suites)
failed = sum(int(s.get("failures", 0)) + int(s.get("errors", 0)) for s in suites)
skipped = sum(int(s.get("skipped", 0)) for s in suites)
assert count >= 90 and failed == 0 and skipped == 0
browser = json.loads((art / "browser-multi-project.json").read_text())
display = json.loads((art / "browser-multi-display.json").read_text())
live = json.loads((art / "live-multi-project.json").read_text())
preserved = json.loads((art / "multi-project-preserved.json").read_text())
assert (
    len(browser["scenarios"]) == 3
    and browser["fresh_project_session"]
    and not browser["page_errors"]
    and not browser["csp_violations"]
)
assert all(
    s["full_lifecycle"]
    and s["unrelated_projects_supported"]
    and s["scoped_tasks"]
    and s["mobile_no_overflow"]
    for s in browser["scenarios"]
)
assert (
    display["final_build"]
    and display["all_projects"]
    and not display["page_errors"]
    and not display["csp_violations"]
)
assert (
    live["live"]
    and live["state_unchanged"]
    and live["graph"] == browser["graph"] == display["graph"]
)
assert len(live["runs"]) == 2 and all(r["status"] == "passed" for r in live["runs"])
assert preserved["state_unchanged"] and preserved["before"] == preserved["after"]
report = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "team": "OmegaRuby",
    "product": "CONTINUUM",
    "scope": "Project/prerequisite-scoped Atlas, Beacon and Orbit workflows",
    "tests": {
        "passed": count,
        "failed": failed,
        "skipped": skipped,
        "duration_seconds": sum(float(s.get("time", 0)) for s in suites),
        "raw_result": "artifacts/pytest-multi-project.xml",
        "warning": "One Starlette HTTPX TestClient adapter deprecation warning",
    },
    "browser": browser,
    "final_build_display": display,
    "live_agent_runs": [
        {
            "project": r["project"],
            "elapsed_ms": r["elapsed_ms"],
            "tools": [t["tool"] for t in r["result"]["trace"]],
        }
        for r in live["runs"]
    ],
    "original_demo_records_preserved": True,
    "normal_demo_readiness": preserved["readiness"],
    "fixture_extension": "Two disclosed synthetic documents, independent Orbit gates and Beacon owners; original source versions retained",
    "build": "TypeScript check + Vite production build passed",
    "limits": [
        "Local single company; project filters are not authorization",
        "Curated synthetic fixture; arbitrary extraction/entailment unverified",
        "Repeated-cycle UX and general event picker unfinished",
        "No public login or verified real reviewer identity",
        "Pagination and larger/concurrent workloads need evaluation",
        "Full Docker execution and another-machine setup unverified",
    ],
}
(art / "multi-project-verification.json").write_text(
    json.dumps(report, indent=2), encoding="utf-8"
)
print(
    json.dumps(
        {k: report[k] for k in ("tests", "live_agent_runs", "normal_demo_readiness")},
        indent=2,
    )
)
