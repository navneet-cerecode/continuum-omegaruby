"""Temporary real-data UI verification server. Ctrl+C deletes only its own graph."""

import os
from pathlib import Path
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["FALKORDB_GRAPH"] = "continuum_gap_" + uuid.uuid4().hex
from backend.graph import Store
from backend.seed import seed

store = Store()
try:
    seed(store)
    store.query(
        "MATCH (v:DocumentVersion {id:'doc-security-approval-v1'}) SET v.valid_to='2020-01-01T00:00:00Z'",
        write=True,
    )
    import uvicorn

    uvicorn.run("backend.main:app", host="127.0.0.1", port=8001)
finally:
    store.graph.delete()
