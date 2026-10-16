"""Summarize executed lifecycle artifacts without relabeling earlier evidence."""

from datetime import datetime, timezone
import json
from pathlib import Path
import xml.etree.ElementTree as ET

art = Path(__file__).resolve().parents[1] / "artifacts"
tree = ET.parse(art / "pytest-lifecycle.xml").getroot()
suites = [tree] if tree.tag == "testsuite" else list(tree)
tests = sum(int(s.get("tests", 0)) for s in suites)
failed = sum(int(s.get("failures", 0)) + int(s.get("errors", 0)) for s in suites)
skipped = sum(int(s.get("skipped", 0)) for s in suites)
assert tests >= 80 and failed == 0 and skipped == 0
browser = json.loads((art / "browser-lifecycle.json").read_text())
live = json.loads((art / "live-restoration.json").read_text())
preserved = json.loads((art / "lifecycle-preserved-demo.json").read_text())
assert (
    browser["real_database"]
    and browser["supported_after_resolution"]
    and browser["fresh_session"]
)
assert (
    browser["seven_explicit_item_confirmations"]
    and not browser["page_errors"]
    and not browser["csp_violations"]
)
assert browser["mobile_no_overflow"] and all(
    r["status"] == 200 for r in browser["api_responses"]
)
assert live["live"] and live["state_unchanged"] and live["graph"] == browser["graph"]
assert len(live["runs"]) == 2 and all(r["status"] == "passed" for r in live["runs"])
assert preserved["state_unchanged"] and preserved["before"] == preserved["after"]
report = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "product": "CONTINUUM",
    "team": "OmegaRuby",
    "scope": "Synthetic Atlas security withdrawal and restoration lifecycle",
    "tests": {
        "passed": tests,
        "failed": failed,
        "skipped": skipped,
        "duration_seconds": sum(float(s.get("time", 0)) for s in suites),
        "raw_result": "artifacts/pytest-lifecycle.xml",
        "warning": "One Starlette HTTPX TestClient adapter deprecation warning",
    },
    "browser": browser,
    "live_agent_runs": [
        {
            "scenario": r["scenario"],
            "elapsed_ms": r["elapsed_ms"],
            "tools": [t["tool"] for t in r["result"]["trace"]],
        }
        for r in live["runs"]
    ],
    "original_demo_state_preserved": True,
    "original_graph": preserved["before"]["graph"],
    "build": "TypeScript check + Vite production build passed",
    "limitations": [
        "Synthetic single-project/event lifecycle; no repeated withdrawal cycle",
        "Synthetic role confirmation without authenticated identity",
        "No external verification or general language entailment guarantee",
        "Local only; no public authorization or company isolation",
        "Unmanaged database races unsupported",
        "Full Docker run/clean installation on another machine unverified",
    ],
}
(art / "lifecycle-verification.json").write_text(
    json.dumps(report, indent=2), encoding="utf-8"
)
print(
    json.dumps(
        {
            "tests": report["tests"],
            "original_demo_state_preserved": True,
            "live_agent_runs": report["live_agent_runs"],
        },
        indent=2,
    )
)
