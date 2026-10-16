import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.graph import Store
from backend.seed import apply_fixture_policies

parser = argparse.ArgumentParser()
parser.add_argument("phase", choices=["before", "migrate", "after"])
args = parser.parse_args()
store = Store()
path = Path("artifacts/hardening-runtime.json")
report = json.loads(path.read_text()) if path.exists() else {}


def snapshot():
    return {
        "actions": sorted(x["action"]["id"] for x in store.actions()),
        "changes": sorted(x["event"]["id"] for x in store.history()),
    }


if args.phase == "before":
    report["before"] = snapshot()
elif args.phase == "migrate":
    apply_fixture_policies(store)
    report["migration"] = (
        "Only missing required prerequisite/source authority fields added; revision advanced."
    )
else:
    report["after"] = snapshot()
    assert report["before"] == report["after"]
    report["existing_history_and_actions_preserved"] = True
path.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
