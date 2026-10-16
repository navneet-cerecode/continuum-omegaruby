"""Aggregate executed release checks, preserving their practical limits."""

from datetime import datetime, timezone
import json
from pathlib import Path
import xml.etree.ElementTree as ET

art = Path(__file__).resolve().parents[1] / "artifacts"


def read(name):
    return json.loads((art / name).read_text(encoding="utf-8-sig"))


tree = ET.parse(art / "pytest-release.xml").getroot()
suites = [tree] if tree.tag == "testsuite" else list(tree)
tests = {
    key: sum(int(s.get(key, 0)) for s in suites)
    for key in ("tests", "failures", "errors", "skipped")
}
assert tests == {"tests": 114, "failures": 0, "errors": 0, "skipped": 0}
browser = read("browser-release.json")
display = read("browser-release-display.json")
cycles = read("browser-release-cycles.json")
assert all(
    browser[key]
    for key in (
        "real_database",
        "account_sessions",
        "role_denial",
        "csrf_denial",
        "company_isolation",
        "preview_before_import",
        "import_actor_recorded",
        "paged_35_records",
        "fresh_authenticated_session",
        "mobile_no_overflow",
    )
)
assert display["final_build"] and display["mobile_no_overflow"]
assert all(
    not proof[key]
    for proof in (browser, display, cycles)
    for key in ("page_errors", "csp_violations")
)
assert cycles["two_cycles_completed"] and cycles["old_snapshot_unchanged"]
model = read("release-model-eval.json")
initial = read("release-model-eval-initial.json")
agent = read("release-agent-ui.json")
assert model["passed"] == 5 and model["model_citation_coverage_complete"] == 5
assert all(row["state_unchanged"] for row in model["runs"])
assert (
    agent["live"]
    and agent["state_unchanged"]
    and agent["result"]["citation_check"]["semantic_entailment"] == "unverified"
)
load = read("release-load.json")
assert load["node_count"] == 1206 and load["impacted_items"] == 127
assert all(
    row["correct"] == 12 and row["explicit_unavailable"] == 0 for row in load["samples"]
)
clean = read("release-clean-install.json")
assert clean["passed"] and not clean["another_machine"]
preserved = read("release-preserved.json")
assert preserved["state_unchanged"] and preserved["before"] == preserved["after"]
python_audit = read("dependency-audit.json")
frontend_audit = read("frontend-dependency-audit.json")
assert not any(row["vulns"] for row in python_audit["dependencies"])
assert frontend_audit["metadata"]["vulnerabilities"]["total"] == 0
video = read("release-video.json")
assert video["actual_recordings"] and not video["uploaded"]
report = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "verification_date_ist": "2026-10-17",
    "team": "OmegaRuby",
    "product": "CONTINUUM",
    "scope": "Optional account/company access, reviewed onboarding, record pages, evidence coverage, load/setup and actual video",
    "tests": {
        "passed": 114,
        "failed": 0,
        "skipped": 0,
        "duration_seconds": sum(float(s.get("time", 0)) for s in suites),
        "raw_result": "artifacts/pytest-release.xml",
        "warning": "One Starlette HTTPX TestClient adapter deprecation warning",
    },
    "browser": browser,
    "final_build_display": display,
    "repeated_cycles_browser": cycles,
    "live_model_evaluation": {
        "passed": 5,
        "scenarios": len(model["runs"]),
        "model_citation_coverage_complete": 5,
        "semantic_entailment": "unverified",
        "initial_failed_cases_retained": sum(
            row["status"] != "passed" for row in initial["runs"]
        ),
        "raw_result": "artifacts/release-model-eval.json",
        "initial_raw_result": "artifacts/release-model-eval-initial.json",
        "timings_ms": {row["scenario"]: row["elapsed_ms"] for row in model["runs"]},
    },
    "live_agent_ui": {
        "live": True,
        "state_unchanged": True,
        "raw_result": "artifacts/release-agent-ui.json",
    },
    "synthetic_load": load,
    "fresh_same_machine_install": clean,
    "original_demo_records_preserved": True,
    "normal_demo_readiness": preserved["readiness"],
    "normal_access_mode": preserved["access_mode"],
    "dependency_audits": {
        "python_known_findings": 0,
        "frontend_known_findings": 0,
        "method": "pip-audit exact pinned inventory and npm audit",
    },
    "video": video,
    "build": "TypeScript/Vite passed; Compose default/account configuration validated; non-root single-worker Dockerfile prepared",
    "ci": "GitHub Actions workflow prepared; no remote execution claimed",
    "outstanding": [
        "Administrator chooses real account credentials and enables accounts if desired; default demo remains explicit",
        "Working Docker engine and full container execution",
        "Another-machine installation",
        "Public repository publication and video upload destination/final review",
        "Participant registration, contribution and technical-understanding sign-off",
        "Final event submission",
        "Automatic arbitrary-format extraction, general semantic entailment and public production operations",
    ],
}
(art / "release-verification.json").write_text(
    json.dumps(report, indent=2), encoding="utf-8"
)
print(
    json.dumps(
        {
            key: report[key]
            for key in ("tests", "live_model_evaluation", "normal_demo_readiness")
        },
        indent=2,
    )
)
