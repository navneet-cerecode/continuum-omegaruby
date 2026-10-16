"""Real FalkorDB lifecycle and concurrency checks; no approval is model-authorized."""

from concurrent.futures import ThreadPoolExecutor
import pytest
from backend.restoration import record, review, approve
from backend.graph import Store
from backend.seed import seed
from backend.service import Continuum
from test_integration import service
from test_api import client


def evidence(revision, reference="SEC-42"):
    return dict(
        expected_revision=revision,
        title="Synthetic replacement security review",
        reference=reference,
        excerpt="Synthetic review passed. Token rotation controls were rechecked and export service approval was restored for the launch cohort.",
        synthetic=True,
        security_approved=True,
    )


def stage(service):
    service.withdraw()
    return record(service.store, evidence(service.store.revision()))


def confirmation(snapshot):
    return dict(
        expected_revision=snapshot["revision"],
        fingerprint=snapshot["fingerprint"],
        reviewer_id=snapshot["candidate_readiness"]["owner_resolution"]["owner"]["id"],
        reviewed_targets=[x["id"] for x in snapshot["impact"]["items"]],
        note="Synthetic launch lead reviewed the new evidence and all affected dependencies.",
        confirm=True,
    )


def test_recording_evidence_is_not_revalidation(service):
    result = stage(service)
    assert result["preview_only"] and result["can_approve"]
    assert result["candidate_readiness"]["status"] == "supported"
    assert service.readiness()["status"] == "review_required"
    assert service.store.entity("approval-export")["state"] == "superseded"
    assert service.store.history()[0]["event"]["state"] == "unresolved"
    assert service.store.impact("approval-export")["count"] == 7
    rev = service.store.revision()
    assert (
        record(service.store, evidence(rev))["review"]["id"] == result["review"]["id"]
    )
    assert service.store.revision() == rev


def test_full_cycle_preserves_history_and_requires_closed_followups(service):
    service.withdraw()
    plan = service.propose()
    service.approve(plan["id"], [plan["proposals"][0]["id"]])
    result = record(service.store, evidence(service.store.revision()))
    assert not result["can_approve"] and result["open_actions"]
    with pytest.raises(ValueError, match="open follow-ups"):
        approve(service.store, result["review"]["id"], confirmation(result))
    task = service.store.actions()[0]["action"]["id"]
    service.transition(task, "completed")
    assert service.readiness()["status"] == "review_required"
    result = review(service.store, result["review"]["id"])
    body = confirmation(result)
    final = approve(service.store, result["review"]["id"], body)
    assert not final["preview_only"] and final["review"]["state"] == "approved"
    assert service.readiness()["status"] == "supported"
    assert service.store.impact("approval-export")["count"] == 0
    assert service.store.impact(result["candidate"]["id"])["count"] == 7
    assert service.store.entity("approval-export-withdrawn")["state"] == "superseded"
    assert service.store.evidence("approval-export")[0]["version"]["excerpt"]
    assert service.store.actions()[0]["action"]["state"] == "completed"
    assert len(service.store.history()) == 1
    assert service.store.history()[0]["event"]["state"] == "resolved"
    assert (
        len(
            service.store.query(
                "MATCH (:RestorationReview)-[:REVALIDATES]->(n) RETURN n.id AS id"
            )
        )
        == 7
    )
    assert service.store.query(
        "MATCH (:Decision {id:'decision-export'})-[r:DEPENDS_ON]->(:Assumption {id:'approval-export'}) RETURN r.current AS current"
    ) == [{"current": False}]
    assert approve(service.store, result["review"]["id"], body)["idempotent"]
    fresh = Continuum(Store(service.store.name))
    assert (
        fresh.readiness()["status"] == "supported"
        and "resolved" in fresh.recap()["conclusion"]
    )
    seed(service.store)
    assert fresh.readiness()["status"] == "supported"
    with pytest.raises(ValueError, match="resolved"):
        service.propose()
    with pytest.raises(ValueError, match="resolved"):
        service.approve(plan["id"], [plan["proposals"][1]["id"]])


def test_replacement_requires_a_withdrawal(service):
    with pytest.raises(ValueError):
        record(service.store, evidence(service.store.revision()))
    assert service.store.restorations() == []


@pytest.mark.parametrize(
    "field,value",
    [
        ("authority", "ticket"),
        ("current", False),
        ("valid_to", "2020-01-01T00:00:00Z"),
        ("valid_from", "2099-01-01T00:00:00Z"),
        ("valid_from", "2020-01-01T00:00:00Z"),
    ],
)
def test_invalid_replacement_source_cannot_resolve(service, field, value):
    snapshot = stage(service)
    service.store.query(
        f"MATCH (v:DocumentVersion {{id:$id}}) SET v.{field}=$value",
        {"id": snapshot["source"]["id"], "value": value},
        write=True,
    )
    latest = review(service.store, snapshot["review"]["id"])
    assert latest["blockers"] and not latest["can_approve"]
    with pytest.raises(ValueError):
        approve(service.store, snapshot["review"]["id"], confirmation(snapshot))
    assert service.store.history()[0]["event"]["state"] == "unresolved"


def test_stale_review_and_partial_or_wrong_owner_signoff_refused(service):
    snapshot = stage(service)
    body = confirmation(snapshot)
    for changes in [
        {"reviewed_targets": body["reviewed_targets"][:-1]},
        {"reviewer_id": "person-6"},
    ]:
        with pytest.raises(ValueError):
            approve(service.store, snapshot["review"]["id"], {**body, **changes})
    service.store.query(
        "MATCH (w:Workspace {id:'workspace'}) SET w.revision=w.revision+1", write=True
    )
    with pytest.raises(ValueError, match="Stale"):
        approve(service.store, snapshot["review"]["id"], body)
    assert service.store.history()[0]["event"]["state"] == "unresolved"


def test_other_prerequisite_gap_blocks_resolution(service):
    snapshot = stage(service)
    service.store.query(
        "MATCH (v:DocumentVersion {id:'doc-capacity-v1'}) SET v.current=false",
        write=True,
    )
    latest = review(service.store, snapshot["review"]["id"])
    assert (
        latest["candidate_readiness"]["status"] == "unknown"
        and not latest["can_approve"]
    )
    with pytest.raises(ValueError):
        approve(service.store, latest["review"]["id"], confirmation(latest))


def test_customer_dependency_expiry_blocks_revalidation(service):
    snapshot = stage(service)
    service.store.query(
        "MATCH (:Commitment {id:'commitment-acme'})-[r:DEPENDS_ON]->() SET r.valid_to='2020-01-01T00:00:00Z'",
        write=True,
    )
    latest = review(service.store, snapshot["review"]["id"])
    assert latest["candidate_readiness"]["status"] == "supported"
    assert not latest["can_approve"] and any(
        "Dependency evidence" in item for item in latest["blockers"]
    )
    with pytest.raises(ValueError):
        approve(service.store, latest["review"]["id"], confirmation(latest))


def test_concurrent_revalidation_never_duplicates_dependencies(service):
    snapshot = stage(service)
    body = confirmation(snapshot)

    def commit():
        try:
            return approve(Store(service.store.name), snapshot["review"]["id"], body)
        except ValueError:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: commit(), range(2)))
    assert any(results)
    assert service.store.query(
        "MATCH ()-[r:DEPENDS_ON]->(:Assumption {id:$id}) RETURN count(r) AS count",
        {"id": snapshot["candidate"]["id"]},
    ) == [{"count": 1}]
    assert (
        len(
            service.store.query(
                "MATCH (:RestorationReview)-[:RESOLVES]->() RETURN 1 AS value"
            )
        )
        == 1
    )


def test_competing_review_cannot_replace_an_already_resolved_event(service):
    first = stage(service)
    second = record(service.store, evidence(service.store.revision(), "SEC-43"))
    first = review(service.store, first["review"]["id"])
    approve(service.store, first["review"]["id"], confirmation(first))
    second = review(service.store, second["review"]["id"])
    assert not second["can_approve"]
    with pytest.raises(ValueError):
        approve(service.store, second["review"]["id"], confirmation(second))


def test_restoration_api_contract_and_explicit_confirmation(client):
    client.post("/api/changes/withdraw-security")
    rev = client.get("/api/overview").json()["revision"]
    assert (
        client.post(
            "/api/restorations", json={**evidence(rev), "security_approved": False}
        ).status_code
        == 422
    )
    response = client.post("/api/restorations", json=evidence(rev))
    assert response.status_code == 200, response.text
    snapshot = response.json()
    assert client.get("/api/restorations/" + snapshot["review"]["id"]).json()[
        "preview_only"
    ]
    body = confirmation(snapshot)
    assert (
        client.post(
            "/api/restorations/" + snapshot["review"]["id"] + "/approve",
            json={**body, "confirm": False},
        ).status_code
        == 422
    )
    response = client.post(
        "/api/restorations/" + snapshot["review"]["id"] + "/approve", json=body
    )
    assert response.status_code == 200, response.text
    assert client.get("/api/readiness").json()["status"] == "supported"
