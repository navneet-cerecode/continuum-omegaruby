"""These tests require real FalkorDB. No graph mocks or in-memory traversal."""

import json
import os
from pathlib import Path
import uuid
import pytest
from backend.graph import Store, GraphUnavailable
from backend.seed import seed, import_markdown
from backend.service import Continuum

EXPECTED = json.loads(
    (Path(__file__).resolve().parents[1] / "data" / "expected-impact.json").read_text()
)


@pytest.fixture
def service():
    store = Store("continuum_test_" + uuid.uuid4().hex)
    seed(store)
    yield Continuum(store)
    store.graph.delete()


def test_expected_impact_and_unrelated_projects(service):
    result = service.store.impact("approval-export")
    ids = {x["id"] for x in result["items"]}
    assert ids == set(EXPECTED["expected"])
    assert not ids.intersection(EXPECTED["excluded"])
    assert next(x for x in result["items"] if x["id"] == "commitment-acme")["path"] == [
        "commitment-acme",
        "milestone-atlas",
        "decision-atlas",
        "milestone-export",
        "decision-export",
        "approval-export",
    ]


def test_dependency_direction_and_graph_is_essential(service):
    before = service.store.impact("approval-export")["count"]
    service.store.query(
        "MATCH (:Decision {id:'decision-atlas'})-[r:DEPENDS_ON]->(:Milestone {id:'milestone-export'}) DELETE r",
        write=True,
    )
    assert service.store.impact("approval-export")["count"] < before
    assert service.store.impact("commitment-acme")["count"] == 0


def test_unrelated_relationship_does_not_propagate(service):
    before = service.store.impact("approval-export")
    service.store.query(
        "MATCH (p:Project {id:'project-beacon'}),(a:Assumption {id:'approval-export'}) CREATE (p)-[:SUPPORTED_BY]->(a)",
        write=True,
    )
    assert [x["id"] for x in service.store.impact("approval-export")["items"]] == [
        x["id"] for x in before["items"]
    ]


def test_withdrawal_history_and_readiness(service):
    assert service.readiness()["status"] == "supported"
    assert service.withdraw()["created"]
    assert not service.withdraw()["created"]
    assert service.readiness()["status"] == "review_required"
    assert service.store.entity("approval-export")["current"] is False
    assert service.store.entity("approval-export")["state"] == "superseded"
    assert service.store.evidence("approval-export")[0]["version"]["excerpt"]
    assert len(service.store.history()) == 1
    assert (
        service.store.evidence("approval-export-withdrawn")[0]["version"]["id"]
        == "doc-security-withdrawal-v1"
    )


def test_owner_conflict_and_missing_owner(service):
    resolution = service.store.owners("project-atlas")
    assert resolution["conflict"]
    assert resolution["owner"]["name"] == "Maya Chen"
    assert {"doc-owner-old-v1", "doc-owner-current-v1"} == {
        x["id"] for x in resolution["sources"]
    }
    assert service.store.owners("approval-export")["owner"] is None


def test_equal_rank_conflict_requires_review(service):
    service.store.query(
        "MATCH (p:Project {id:'project-atlas'}),(n:Person {id:'person-6'}) CREATE (p)-[:OWNED_BY {current:true,authority:100,valid_from:'2026-10-16T07:00:00Z',source:'doc-owner-old-v1'}]->(n)",
        write=True,
    )
    resolution = service.store.owners("project-atlas")
    assert resolution["ambiguous"] and resolution["owner"] is None


def test_cycles_and_duplicate_paths_are_bounded(service):
    service.store.query(
        "MATCH (a:Decision {id:'decision-atlas'}),(b:Decision {id:'decision-export'}) CREATE (b)-[:DEPENDS_ON {source:'doc-export-decision-v1'}]->(a) CREATE (a)-[:DEPENDS_ON {source:'doc-atlas-decision-v1'}]->(b)",
        write=True,
    )
    result = service.store.impact("approval-export")
    assert {x["id"] for x in result["items"]} == set(EXPECTED["expected"])
    assert len(result["items"]) == len(set(x["id"] for x in result["items"]))
    assert all(len(x["path"]) <= 9 for x in result["items"])


def test_seed_idempotent_does_not_restore_old_approval(service):
    before = service.store.query("MATCH (n) RETURN count(n) AS count")[0]["count"]
    rev = service.store.revision()
    assert seed(service.store)["imported_documents"] == 0
    assert service.store.revision() == rev
    assert (
        service.store.query("MATCH (n) RETURN count(n) AS count")[0]["count"] == before
    )
    edges = service.store.query("MATCH ()-[r]->() RETURN count(r) AS count")[0]["count"]
    seed(service.store)
    assert (
        service.store.query("MATCH ()-[r]->() RETURN count(r) AS count")[0]["count"]
        == edges
    )
    service.withdraw()
    seed(service.store)
    assert service.store.entity("approval-export")["current"] is False


def test_approved_tasks_actual_links_and_idempotency(service):
    service.withdraw()
    plan = service.propose()
    assert len(plan["proposals"]) == 4
    assert service.store.actions() == []
    selection = [plan["proposals"][0]["id"], plan["proposals"][1]["id"]]
    result = service.approve(plan["id"], selection)
    assert result["created"] == 2
    assert service.approve(plan["id"], selection)["created"] == 0
    assert len(service.store.actions()) == 2
    relations = service.store.query(
        "MATCH (a:ActionItem)-[r]->() RETURN a.id AS id,collect(type(r)) AS relations"
    )
    assert all(
        set(x["relations"])
        == {
            "ASSIGNED_TO",
            "FOR_DECISION",
            "TRIGGERED_BY",
            "SUPPORTED_BY",
            "CREATED_FROM",
        }
        for x in relations
    )


def test_stale_plan_refused(service):
    service.withdraw()
    plan = service.propose()
    service.store.query(
        "MATCH (w:Workspace {id:'workspace'}) SET w.revision=w.revision+1", write=True
    )
    with pytest.raises(ValueError, match="Stale"):
        service.approve(plan["id"], [plan["proposals"][0]["id"]])
    assert service.store.actions() == []


def test_external_supporting_edge_change_is_stale(service):
    service.withdraw()
    plan = service.propose()
    service.store.query(
        "MATCH (:Commitment {id:'commitment-acme'})-[r:DEPENDS_ON]->() DELETE r",
        write=True,
    )
    with pytest.raises(ValueError, match="Stale"):
        service.approve(plan["id"], [plan["proposals"][0]["id"]])
    assert service.store.actions() == []


def test_selection_from_different_plan_rejected(service):
    service.withdraw()
    plan = service.propose()
    with pytest.raises(ValueError, match="Selection"):
        service.approve(plan["id"], ["proposal-unknown"])


def test_completion_does_not_resolve_underlying_risk(service):
    service.withdraw()
    plan = service.propose()
    service.approve(plan["id"], [plan["proposals"][0]["id"]])
    action = service.store.actions()[0]["action"]["id"]
    service.transition(action, "completed")
    assert service.readiness()["status"] == "review_required"
    assert service.store.history()[0]["event"]["state"] == "unresolved"
    assert service.recap()["unresolved_actions"] == []


def test_fresh_store_session_preserves_actions(service):
    service.withdraw()
    plan = service.propose()
    service.approve(plan["id"], [plan["proposals"][0]["id"]])
    fresh = Continuum(Store(service.store.name))
    assert len(fresh.recap()["actions"]) == 1
    assert len(fresh.recap()["changes"]) == 1
    assert fresh.readiness()["status"] == "review_required"


def test_missing_path_is_unknown_not_safe(service):
    result = service.store.impact("approval-beacon")
    assert "project-atlas" not in {x["id"] for x in result["items"]}
    assert "absence of risk" in result["caveat"]


def test_immutable_markdown_versions(service, tmp_path):
    source = Path(__file__).resolve().parents[1] / "data" / "documents" / "acme.md"
    assert not import_markdown(service.store, source)
    changed = tmp_path / "changed.md"
    changed.write_text(source.read_text() + "Altered evidence")
    with pytest.raises(ValueError, match="immutable"):
        import_markdown(service.store, changed)


def test_new_version_preserves_historical_decision_source(service, tmp_path):
    source = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "documents"
        / "security-approval.md"
    )
    raw = source.read_text()
    header, body = raw[8:].split("\n---\n", 1)
    meta = json.loads(header)
    meta.update(
        id="doc-security-approval-v2",
        version=2,
        supersedes="doc-security-approval-v1",
        valid_from="2026-10-16T09:00:00Z",
        subjects=[],
    )
    new = tmp_path / "new-version.md"
    new.write_text(
        "---json\n" + json.dumps(meta) + "\n---\nA revised review is pending."
    )
    assert import_markdown(service.store, new)
    assert service.store.entity("doc-security-approval-v1")["current"] is False
    assert service.store.entity("doc-security-approval-v2")["current"] is True
    assert "doc-security-approval-v1" in {
        x["version"]["id"] for x in service.store.evidence("approval-export")
    }


def test_unavailable_database_has_no_fallback():
    with pytest.raises(GraphUnavailable):
        Store("continuum_unavailable", port=6399).search("Atlas")


def test_parameterized_search_cannot_inject(service):
    assert service.store.search("' MATCH (n) DETACH DELETE n //") == []
    assert service.store.entity("project-atlas")["name"] == "Project Atlas"
    with pytest.raises(ValueError):
        service.store.entity("x' DELETE n")
