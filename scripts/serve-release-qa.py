"""Own two account-scoped QA graphs and temporary test credentials."""

import argparse
import json
import os
from pathlib import Path
import re
import secrets
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.graph import Store  # noqa: E402
from backend.seed import seed  # noqa: E402
from backend.access import password_hash  # noqa: E402

path = ROOT / ".runtime/release-qa.json"
account_path = ROOT / ".runtime/release-qa-accounts.json"
parser = argparse.ArgumentParser()
parser.add_argument("--cleanup", action="store_true")
args = parser.parse_args()


def cleanup():
    data = json.loads(path.read_text(encoding="utf-8"))
    for name in data["graphs"]:
        if not re.fullmatch("continuum_releaseqa_[a-f0-9]{32}", name):
            raise ValueError("Unowned QA graph")
        s = Store(name)
        if s.entity("release-qa-marker")["name"] != name:
            raise ValueError("QA marker mismatch")
        s.graph.delete()
    path.unlink()
    account_path.unlink(missing_ok=True)
    print("Deleted only the two owned account QA graphs and test credential files")


if args.cleanup:
    cleanup()
else:
    if path.exists():
        raise SystemExit(
            "An owned QA manifest already exists; clean up its graphs first"
        )
    names = ["continuum_releaseqa_" + uuid.uuid4().hex for _ in range(2)]
    for name in names:
        s = Store(name)
        seed(s)
        s.query(
            "CREATE (:VerificationMarker {id:'release-qa-marker',name:$name})",
            {"name": name},
            write=True,
        )
        s.query(
            "MATCH (p:Project {id:'project-atlas'}) UNWIND range(1,35) AS i CREATE (e:ChangeEvent {id:'qa-record-'+toString(i),name:'Synthetic QA paging record',state:'test-record',created_at:'2026-10-17T01:00:00Z'}) CREATE (e)-[:AFFECTS]->(p)",
            write=True,
        )
    password = secrets.token_urlsafe(24)
    encoded = password_hash(password)
    accounts = {
        "companies": {"alpha": {"graph": names[0]}, "beta": {"graph": names[1]}},
        "users": {},
    }
    for username, company, role in (
        ("reader", "alpha", "viewer"),
        ("admin", "alpha", "admin"),
        ("other", "beta", "admin"),
    ):
        accounts["users"][username] = {
            "company": company,
            "role": role,
            "person_id": "person-1",
            "password_hash": encoded,
        }
    path.parent.mkdir(exist_ok=True)
    path.write_text(
        json.dumps({"graphs": names, "password": password}), encoding="utf-8"
    )
    account_path.write_text(json.dumps(accounts), encoding="utf-8")
    os.environ["CONTINUUM_ACCESS"] = "accounts"
    os.environ["CONTINUUM_ACCOUNTS_FILE"] = str(account_path)
    os.environ["FALKORDB_GRAPH"] = names[0]
    try:
        import uvicorn

        uvicorn.run("backend.main:app", host="127.0.0.1", port=8000)
    finally:
        cleanup()
