"""Small-fixture local measurements. Never claim enterprise scale from these."""

import json
import os
import platform
from pathlib import Path
import statistics
from time import perf_counter
import uuid
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.graph import Store
from backend.seed import seed

QUERY = (
    "MATCH p=(n)-[:DEPENDS_ON*1..8]->(a {id:$id}) RETURN DISTINCT n.id AS id LIMIT 200"
)


def measure(fn, n=50):
    for _ in range(5):
        fn()
    samples = []
    for _ in range(n):
        start = perf_counter()
        fn()
        samples.append((perf_counter() - start) * 1000)
    ordered = sorted(samples)
    return {
        "samples": n,
        "warmups": 5,
        "median_ms": round(statistics.median(samples), 3),
        "p95_ms": round(ordered[int(0.95 * (n - 1))], 3),
        "min_ms": round(min(samples), 3),
        "max_ms": round(max(samples), 3),
    }


if __name__ == "__main__":
    store = Store("continuum_benchmark_" + uuid.uuid4().hex)
    try:
        seed(store)
        size = store.query("MATCH (n) RETURN count(n) AS nodes")[0]
        size.update(store.query("MATCH ()-[r]->() RETURN count(r) AS relationships")[0])
        expected = json.loads(
            (
                Path(__file__).resolve().parents[1] / "data" / "expected-impact.json"
            ).read_text()
        )
        actual = {x["id"] for x in store.query(QUERY, {"id": "approval-export"})}
        assert actual == set(expected["expected"])
        report = {
            "dataset": size,
            "documents": 24,
            "expected_impact": 7,
            "actual_impact": len(actual),
            "correctness": "Exact expected ID set, independently specified fixture",
            "machine": {
                "os": platform.platform(),
                "cpu": platform.processor(),
                "logical_processors": os.cpu_count(),
                "python": platform.python_version(),
            },
            "database": "Official FalkorDB 4.14.11 on Redis 8.0.5 in Ubuntu WSL, AOF on checkout filesystem",
            "concurrency": 1,
            "method": "perf_counter round-trip wall time; warm caches; seed time excluded",
            "dependency_query": measure(
                lambda: store.query(QUERY, {"id": "approval-export"})
            ),
            "full_evidence_hydration": measure(
                lambda: store.impact("approval-export"), n=30
            ),
            "model_latency": "Measured separately by live agent verification; excluded here",
            "scale_claim": "Small fixture only. No enterprise/concurrent-load claim.",
        }
        Path("artifacts").mkdir(exist_ok=True)
        Path("artifacts/benchmark.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        print(json.dumps(report, indent=2))
    finally:
        if store.graph:
            store.graph.delete()
