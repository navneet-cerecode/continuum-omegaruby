"""Own an isolated loopback lifecycle demo graph; never reseed the user's graph."""

import argparse
import os
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
path = ROOT / ".runtime/lifecycle-qa-graph.txt"
parser = argparse.ArgumentParser()
parser.add_argument("--cleanup", action="store_true")
args = parser.parse_args()
from backend.graph import Store
from backend.seed import seed

if args.cleanup:
    name = path.read_text().strip()
    assert (
        name.startswith("continuum_lifecycle_")
        and len(name) == len("continuum_lifecycle_") + 32
    )
    store = Store(name)
    assert store.entity("workspace")["synthetic"] is True
    store.graph.delete()
    path.unlink()
    print("Deleted only owned lifecycle QA graph " + name)
else:
    name = "continuum_lifecycle_" + uuid.uuid4().hex
    os.environ["FALKORDB_GRAPH"] = name
    path.parent.mkdir(exist_ok=True)
    path.write_text(name)
    store = Store(name)
    seed(store)
    store.query(
        "CREATE (:VerificationMarker {id:'lifecycle-qa-marker',name:$name,synthetic:true})",
        {"name": name},
        write=True,
    )
    print("Isolated verification graph: " + name, flush=True)
    try:
        import uvicorn

        uvicorn.run("backend.main:app", host="127.0.0.1", port=8000)
    finally:
        store.graph.delete()
        path.unlink(missing_ok=True)
