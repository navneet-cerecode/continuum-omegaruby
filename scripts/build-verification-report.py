import json
from pathlib import Path
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parents[1]
art = root / "artifacts"
raw_result = next(
    name
    for name in (
        "pytest-release.xml",
        "pytest-cycles.xml",
        "pytest-multi-project.xml",
        "pytest-lifecycle.xml",
        "pytest-hardening.xml",
    )
    if (art / name).exists()
)
tree = ET.parse(art / raw_result).getroot()
suites = [tree] if tree.tag == "testsuite" else list(tree)
test_count = sum(int(s.attrib.get("tests", 0)) for s in suites)
failures = sum(
    int(s.attrib.get("failures", 0)) + int(s.attrib.get("errors", 0)) for s in suites
)
browser = json.loads((art / "browser-verification.json").read_text())
agent = json.loads((art / "live-agent.json").read_text())
injection = json.loads((art / "live-injection.json").read_text())
runtime = json.loads((art / "runtime-verification.json").read_text())
assert test_count >= 32 and failures == 0
assert (
    browser["live_model_run"]
    and browser["fresh_session"]
    and browser["focused_edge_evidence_verified"]
)
assert all(r["status"] == "passed" for r in agent["runs"])
assert injection["actions_unchanged"] and runtime["restart_preserved_state"]
report = {
    "team": "OmegaRuby",
    "product": "CONTINUUM",
    "track": "Track 3 — Company Brain",
    "verification_date_ist": "2026-10-17",
    "tests": {
        "passed": test_count,
        "failed": failures,
        "duration_seconds": sum(float(s.attrib.get("time", 0)) for s in suites),
        "raw_result": "artifacts/" + raw_result,
        "warning": "One Starlette HTTPX TestClient adapter deprecation warning",
    },
    "database": "Real official FalkorDB 4.14.11 + Redis 8.0.5 in Ubuntu WSL, persistent AOF",
    "model": "Free local Ollama 0.40.4 + installed llama3:latest, no account/API key",
    "live_agent_runs": [
        {
            "scenario": r["scenario"],
            "elapsed_ms": r["elapsed_ms"],
            "tools": [t["tool"] for t in r["result"]["trace"]],
        }
        for r in agent["runs"]
    ],
    "live_prompt_injection_actions_unchanged": True,
    "baseline_browser": browser,
    "hardening": json.loads((art / "hardening-verification.json").read_text()),
    "lifecycle": json.loads((art / "lifecycle-verification.json").read_text()),
    "multi_project": json.loads((art / "multi-project-verification.json").read_text()),
    "cycles": json.loads(
        (art / "cycles-verification.json").read_text(encoding="utf-8")
    ),
    "release": json.loads(
        (art / "release-verification.json").read_text(encoding="utf-8")
    ),
    "database_and_backend_restart_preserved_state": True,
    "actual_database_outage_status": runtime["database_outage"]["status"],
    "build": "TypeScript + Vite production build passed; Compose configuration validated",
    "outstanding": [
        "Complete Docker image run on working engine",
        "Clean installation on another machine",
        "Public repository publication",
        "Demo video upload; actual local recording supplied",
        "Human contribution and understanding sign-off",
        "Registration/submission confirmation",
    ],
    "claims_excluded": [
        "General arbitrary-document extraction",
        "Enterprise scale",
        "Production readiness",
        "Public deployment",
        "Verified participant understanding",
    ],
}
(art / "verification.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(
    json.dumps(
        {
            k: report[k]
            for k in (
                "team",
                "tests",
                "model",
                "database_and_backend_restart_preserved_state",
            )
        },
        indent=2,
    )
)
