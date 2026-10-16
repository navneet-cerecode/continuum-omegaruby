"""Summarize executed repeated-cycle evidence without broad model claims."""

from datetime import datetime, timezone
import json
from pathlib import Path
import xml.etree.ElementTree as ET

art = Path(__file__).resolve().parents[1] / "artifacts"
tree = ET.parse(art / "pytest-cycles.xml").getroot()
suites = [tree] if tree.tag == "testsuite" else list(tree)
count = sum(int(s.get("tests", 0)) for s in suites)
failed = sum(int(s.get("failures", 0)) + int(s.get("errors", 0)) for s in suites)
skipped = sum(int(s.get("skipped", 0)) for s in suites)
assert count >= 103 and failed == 0 and skipped == 0


def read(name):
    return json.loads((art / name).read_text(encoding="utf-8"))


browser = read("browser-cycles.json")
display = read("browser-cycles-display.json")
live = read("live-cycles.json")
preserved = read("cycles-preserved.json")
assert browser["real_database"] and browser["two_cycles_completed"]
assert len(set(browser["events"])) == len(set(browser["tasks"])) == 2
assert all(
    browser[key]
    for key in (
        "old_snapshot_unchanged",
        "historical_read_only_during_active_withdrawal",
        "fresh_history_selection",
        "mobile_no_overflow",
    )
)
assert all(row["status"] == 200 for row in browser["api_responses"])
assert all(
    display[key]
    for key in (
        "final_build",
        "historical_graph_label",
        "owner_at_withdrawal_label",
        "mobile_no_overflow",
    )
)
assert all(
    not proof[key]
    for proof in (browser, display)
    for key in ("page_errors", "csp_violations")
)
assert live["graph"] == browser["graph"] == display["graph"]
assert live["live"] and live["model_state_unchanged"]
assert len(live["runs"]) == 2 and all(r["status"] == "passed" for r in live["runs"])
assert live["setup_third_event_id"] not in browser["events"]
assert preserved["state_unchanged"] and preserved["before"] == preserved["after"]
assert preserved["health"]["database"] == "available"
assert preserved["readiness"] == {
    "atlas": "review_required",
    "beacon": "supported",
    "orbit": "supported",
}
report = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "verification_date_ist": "2026-10-17",
    "team": "OmegaRuby",
    "product": "CONTINUUM",
    "scope": "Repeated approval cycles and historical incident selection",
    "tests": {
        "passed": count,
        "failed": failed,
        "skipped": skipped,
        "duration_seconds": sum(float(s.get("time", 0)) for s in suites),
        "raw_result": "artifacts/pytest-cycles.xml",
        "warning": "One Starlette HTTPX TestClient adapter deprecation warning",
    },
    "browser": browser,
    "final_build_display": display,
    "live_agent_runs": [
        {
            "scenario": r["scenario"],
            "elapsed_ms": r["elapsed_ms"],
            "tools": [t["tool"] for t in r["result"]["trace"]],
            "conclusion": r["result"]["answer"]["conclusion"],
        }
        for r in live["runs"]
    ],
    "live_model_state_unchanged": True,
    "original_demo_records_preserved": True,
    "normal_demo_readiness": preserved["readiness"],
    "normal_demo_revision": preserved["health"]["revision"],
    "build": "TypeScript check + Vite production build passed",
    "limits": [
        "Historical model prose selected only ownership citations, repeated a path and gave a weak conflict description; membership checks do not establish entailment",
        "Legacy history is reconstructed, not an event-time snapshot",
        "SHA-256 snapshot checksum is not an administrator-resistant signature",
        "Picker lists 100 recent project incidents; older known IDs have direct access",
        "Local synthetic company; project selection is not authorization",
        "Arbitrary extraction, authenticated reviewers and larger workload evaluation unfinished",
        "Full Docker execution and another-machine setup unverified",
    ],
}
(art / "cycles-verification.json").write_text(
    json.dumps(report, indent=2), encoding="utf-8"
)
print(
    json.dumps(
        {
            key: report[key]
            for key in ("tests", "live_agent_runs", "normal_demo_readiness")
        },
        indent=2,
    )
)
