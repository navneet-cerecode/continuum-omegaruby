"""Bounded synthetic load experiment on an owned real FalkorDB graph."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import statistics
import sys
from time import perf_counter
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.graph import Store, GraphUnavailable  # noqa: E402
from backend.seed import seed  # noqa: E402

name = "continuum_load_" + uuid.uuid4().hex
s = Store(name)
report = {
    "verified_at": datetime.now(timezone.utc).isoformat(),
    "graph": name,
    "real_database": True,
    "synthetic": True,
    "machine": platform.platform(),
    "samples": [],
}
try:
    seed(s)
    s.query(
        """MATCH (a:Assumption {id:'approval-export'}),(owner:Person {id:'person-4'}),(v:DocumentVersion {id:'doc-security-approval-v1'})
    UNWIND range(1,120) AS i CREATE (n:Decision {id:'load-decision-'+toString(i),name:'Synthetic dependent decision',state:'approved',classification:'confirmed'})
    CREATE (n)-[:DEPENDS_ON {id:'load-edge-'+toString(i),source:v.id,current:true,valid_from:'2026-10-15T00:00:00Z'}]->(a),
    (n)-[:OWNED_BY {authority:100,current:true,source:'doc-owner-current-v1',valid_from:'2026-10-15T00:00:00Z'}]->(owner),(n)-[:SUPPORTED_BY]->(v)""",
        write=True,
    )
    s.query(
        "UNWIND range(1,1000) AS i CREATE (:Person {id:'load-unrelated-'+toString(i),name:'Unrelated synthetic record'})",
        write=True,
    )
    expected = {item["id"] for item in Store(name).impact("approval-export")["items"]}
    assert len(expected) == 127
    for concurrency in (1, 4):

        def sample(_):
            start = perf_counter()
            try:
                result = Store(name).impact("approval-export")
                assert {item["id"] for item in result["items"]} == expected
                assert not result["truncated"] and result["sourced"]
                return {
                    "ms": round((perf_counter() - start) * 1000, 3),
                    "status": "correct",
                }
            except GraphUnavailable:
                return {
                    "ms": round((perf_counter() - start) * 1000, 3),
                    "status": "explicit_unavailable",
                }

        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            values = list(pool.map(sample, range(12)))
        times = sorted(row["ms"] for row in values)
        report["samples"].append(
            {
                "concurrency": concurrency,
                "runs": values,
                "median_ms": round(statistics.median(times), 3),
                "p95_observed_ms": times[int(0.95 * (len(times) - 1))],
                "correct": sum(row["status"] == "correct" for row in values),
                "explicit_unavailable": sum(
                    row["status"] == "explicit_unavailable" for row in values
                ),
            }
        )
    report["node_count"] = s.query("MATCH (n) RETURN count(n) AS count")[0]["count"]
    report["impacted_items"] = 127
    report["unrelated_records_excluded"] = 1000
    report["limits"] = (
        "Small synthetic experiment with 12 samples per concurrency. No enterprise capacity, SLA or independent hardware claim."
    )
    assert all(sample["correct"] for sample in report["samples"])
finally:
    if s.graph is not None:
        s.graph.delete()
    report["owned_graph_cleaned"] = True
    (ROOT / "artifacts/release-load.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
print(
    json.dumps(
        {k: report[k] for k in ("node_count", "impacted_items", "samples")}, indent=2
    )
)
