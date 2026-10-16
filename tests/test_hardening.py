"""Regression scenarios for incomplete evidence, ownership and guarded imports."""

import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pytest
from backend.seed import import_markdown
from backend.graph import Store
from test_integration import service


def codes(result):
    return {i["code"] for i in result["issues"]}


def test_missing_security_path_cannot_be_supported_by_capacity_alone(service):
    service.store.query(
        "MATCH (:Decision {id:'decision-export'})-[r:DEPENDS_ON]->(:Assumption {id:'approval-export'}) DELETE r",
        write=True,
    )
    result = service.readiness()
    assert result["status"] == "unknown" and "missing_prerequisite" in codes(result)


@pytest.mark.parametrize(
    "property,value",
    [
        ("current", False),
        ("valid_to", "2020-01-01T00:00:00Z"),
        ("valid_from", "2099-01-01T00:00:00Z"),
        ("excerpt", ""),
        ("classification", "disputed"),
    ],
)
def test_invalid_security_source_never_supports_launch(service, property, value):
    service.store.query(
        f"MATCH (v:DocumentVersion {{id:'doc-security-approval-v1'}}) SET v.{property}=$value",
        {"value": value},
        write=True,
    )
    result = service.readiness()
    assert result["status"] == "unknown" and "missing_current_evidence" in codes(result)
    assert service.store.evidence("approval-export"), (
        "Historical evidence remains inspectable"
    )


def test_ticket_does_not_substitute_for_authoritative_security_review(service):
    service.store.query(
        "MATCH (:Assumption {id:'approval-export'})-[r:SUPPORTED_BY]->(:DocumentVersion {id:'doc-security-approval-v1'}) DELETE r",
        write=True,
    )
    assert (
        service.store.evidence("approval-export")[0]["version"]["authority"] == "ticket"
    )
    assert service.readiness()["status"] == "unknown"


def test_missing_project_policy_is_unknown(service):
    service.store.query(
        "MATCH (p:Project {id:'project-atlas'}) REMOVE p.required_assumptions",
        write=True,
    )
    assert "missing_readiness_policy" in codes(service.readiness())


def test_malformed_project_policy_is_unknown(service):
    service.store.query(
        "MATCH (p:Project {id:'project-atlas'}) SET p.required_assumptions=[42]",
        write=True,
    )
    assert "missing_readiness_policy" in codes(service.readiness())


def test_readiness_path_limit_is_explicit(service):
    service.store.query(
        "MATCH (d:Decision {id:'decision-export'}),(a:Assumption {id:'assumption-capacity'}) UNWIND range(1,60) AS i CREATE (d)-[:DEPENDS_ON {current:true,source:'doc-export-decision-v1',test_index:i}]->(a)",
        write=True,
    )
    result = service.readiness()
    assert (
        result["status"] == "unknown" and not result["complete"] and result["truncated"]
    )
    assert "path_limit" in codes(result)


def test_depth_limit_is_explicit(service):
    previous = "project-atlas"
    for i in range(1, 10):
        id = f"depth-test-{i}"
        service.store.query(
            "CREATE (n:Decision {id:$id,name:$id})", {"id": id}, write=True
        )
        service.store.query(
            "MATCH (a {id:$a}),(b {id:$b}) CREATE (a)-[:DEPENDS_ON {current:true,source:'doc-launch-checklist-v1'}]->(b)",
            {"a": previous, "b": id},
            write=True,
        )
        previous = id
    result = service.readiness()
    assert (
        result["status"] == "unknown"
        and not result["complete"]
        and "depth_limit" in codes(result)
    )


def test_all_top_ranked_owners_must_agree_even_with_duplicates(service):
    service.store.query(
        "MATCH (p:Project {id:'project-atlas'}),(a:Person {id:'person-1'}),(b:Person {id:'person-6'}) CREATE (p)-[:OWNED_BY {current:true,authority:100,valid_from:'2026-10-16T07:00:00Z',source:'doc-owner-current-v1'}]->(a) CREATE (p)-[:OWNED_BY {current:true,authority:100,valid_from:'2026-10-16T07:00:00Z',source:'doc-owner-old-v1'}]->(b)",
        write=True,
    )
    resolution = service.store.owners("project-atlas")
    assert resolution["ambiguous"] and resolution["owner"] is None
    assert service.readiness()["status"] == "review_required"


def test_future_owner_does_not_take_over_early(service):
    service.store.query(
        "MATCH (p:Project {id:'project-atlas'}),(n:Person {id:'person-6'}) CREATE (p)-[:OWNED_BY {current:true,authority:200,valid_from:'2099-01-01T00:00:00Z',source:'doc-owner-old-v1'}]->(n)",
        write=True,
    )
    assert service.store.owners("project-atlas")["owner"]["id"] == "person-1"


def test_missing_owner_source_is_surfaced_without_crash(service):
    service.store.query(
        "MATCH (:Project {id:'project-atlas'})-[r:OWNED_BY]->(:Person {id:'person-1'}) SET r.source='doc-does-not-exist-v1'",
        write=True,
    )
    assert service.store.owners("project-atlas")["owner"] is None
    assert "unresolved_owner" in codes(service.readiness())


def document(tmp_path, **overrides):
    meta = {
        "id": "doc-new-v1",
        "document_id": "doc-new",
        "title": "New synthetic evidence",
        "version": 1,
        "valid_from": "2026-10-16T10:00:00Z",
        "authority": "security",
        "synthetic": True,
        "subjects": ["approval-export"],
    }
    meta.update(overrides)
    path = tmp_path / (meta["id"] + ".md")
    path.write_text(
        "---json\n" + json.dumps(meta) + "\n---\nA clearly synthetic source excerpt.",
        encoding="utf-8",
    )
    return path


def snapshot(store):
    return (
        store.revision(),
        store.query("MATCH (n) RETURN count(n) AS count")[0]["count"],
        store.query("MATCH ()-[r]->() RETURN count(r) AS count")[0]["count"],
    )


@pytest.mark.parametrize(
    "overrides",
    [
        {"version": True},
        {"version": "2"},
        {"valid_from": "2026-10-16"},
        {"subjects": ["missing-person"]},
        {"synthetic": False},
        {"unexpected": "override instructions"},
        {"id": "person-1"},
        {"document_id": "person-1"},
    ],
)
def test_invalid_import_has_no_partial_state(service, tmp_path, overrides):
    before = snapshot(service.store)
    with pytest.raises(ValueError):
        import_markdown(service.store, document(tmp_path, **overrides))
    assert snapshot(service.store) == before


def test_duplicate_current_document_version_rejected(service, tmp_path):
    before = snapshot(service.store)
    path = document(
        tmp_path,
        id="doc-security-approval-v2",
        document_id="doc-security-approval",
        version=2,
    )
    with pytest.raises(ValueError, match="supersede"):
        import_markdown(service.store, path)
    assert snapshot(service.store) == before


def test_concurrent_imports_cannot_create_two_current_versions(service, tmp_path):
    first = document(
        tmp_path,
        id="doc-security-approval-v2",
        document_id="doc-security-approval",
        version=2,
        supersedes="doc-security-approval-v1",
    )
    second = document(
        tmp_path,
        id="doc-security-approval-v3",
        document_id="doc-security-approval",
        version=3,
        supersedes="doc-security-approval-v1",
    )

    def attempt(path):
        try:
            return import_markdown(Store(service.store.name), path)
        except ValueError:
            return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, [first, second]))
    assert sum(results) == 1
    current = service.store.query(
        "MATCH (v:DocumentVersion)-[:PART_OF]->(:Document {id:'doc-security-approval'}) WHERE v.current=true RETURN v.id AS id"
    )
    assert len(current) == 1
    assert service.store.entity("doc-security-approval-v1")["current"] is False


def test_subject_disappearing_before_write_leaves_no_import(
    service, tmp_path, monkeypatch
):
    original = service.store.query
    revision = service.store.revision()

    def race(cypher, params=None, write=False):
        if write and "FOREACH (subject IN subjects" in cypher:
            original("MATCH (p:Person {id:'person-12'}) DETACH DELETE p", write=True)
        return original(cypher, params, write)

    monkeypatch.setattr(service.store, "query", race)
    with pytest.raises(ValueError, match="Graph changed"):
        import_markdown(service.store, document(tmp_path, subjects=["person-12"]))
    assert service.store.revision() == revision
    assert (
        service.store.query("MATCH (v {id:'doc-new-v1'}) RETURN count(v) AS count")[0][
            "count"
        ]
        == 0
    )


def test_truncated_impact_cannot_generate_tasks(service):
    service.withdraw()
    service.store.query(
        "MATCH (d:Decision {id:'decision-export'}),(a:Assumption {id:'approval-export'}) UNWIND range(1,210) AS i CREATE (d)-[:DEPENDS_ON {source:'doc-export-decision-v1',test_index:i}]->(a)",
        write=True,
    )
    with pytest.raises(ValueError, match="incomplete"):
        service.propose()
    assert service.store.actions() == []
