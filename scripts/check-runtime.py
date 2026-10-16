"""Capture real restart/outage evidence without changing organizational state."""

import argparse
import json
from pathlib import Path
import httpx

parser = argparse.ArgumentParser()
parser.add_argument("phase", choices=["before", "outage", "after"])
args = parser.parse_args()
path = Path("artifacts/runtime-verification.json")
report = json.loads(path.read_text()) if path.exists() else {}
with httpx.Client(base_url="http://127.0.0.1:8000", timeout=10) as c:
    if args.phase == "outage":
        r = c.get("/api/health")
        assert r.status_code == 503 and r.json()["dependency"] == "FalkorDB"
        report["database_outage"] = {"status": r.status_code, "body": r.json()}
    else:
        data = c.get("/api/recap").json()
        item = {
            "change_ids": [x["event"]["id"] for x in data["changes"]],
            "action_ids": sorted(x["action"]["id"] for x in data["actions"]),
        }
        assert item["change_ids"] and item["action_ids"]
        report[args.phase] = item
        if args.phase == "after":
            assert report["before"] == report["after"]
            report["restart_preserved_state"] = True
path.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
