"""Provision local accounts interactively; passwords never enter CLI arguments."""

import argparse
from getpass import getpass
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.access import password_hash
from backend.graph import valid_id

parser = argparse.ArgumentParser()
parser.add_argument("username")
parser.add_argument("--company", required=True)
parser.add_argument("--graph", required=True)
parser.add_argument(
    "--role", choices=("viewer", "editor", "reviewer", "admin"), default="viewer"
)
parser.add_argument(
    "--person-id", help="Recorded Person ID required for restoration reviewers"
)
parser.add_argument("--file", default=".runtime/accounts.json")
args = parser.parse_args()
for value in (args.username, args.company, args.graph, args.person_id):
    if value:
        valid_id(value)
path = Path(args.file)
data = (
    json.loads(path.read_text(encoding="utf-8"))
    if path.exists()
    else {"companies": {}, "users": {}}
)
existing = data["companies"].get(args.company)
if existing and existing["graph"] != args.graph:
    raise SystemExit(
        "Company graph mapping cannot be changed through account provisioning"
    )
if any(
    c != args.company and v["graph"] == args.graph for c, v in data["companies"].items()
):
    raise SystemExit("This graph is already assigned to another company")
password = getpass("Password (15–256 characters): ")
if password != getpass("Confirm password: "):
    raise SystemExit("Passwords did not match")
user = {
    "company": args.company,
    "role": args.role,
    "password_hash": password_hash(password),
}
if args.person_id:
    user["person_id"] = args.person_id
data["companies"][args.company] = {"graph": args.graph}
data["users"][args.username] = user
path.parent.mkdir(parents=True, exist_ok=True)
temp = path.with_suffix(".tmp")
temp.write_text(json.dumps(data, indent=2), encoding="utf-8")
temp.replace(path)
print(
    "Account saved. Keep this file private. Enable CONTINUUM_ACCESS=accounts and restart the app."
)
