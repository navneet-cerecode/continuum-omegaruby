import pytest
from test_integration import service


def test_impact_depth_boundary_refuses_response_plan(service):
    service.withdraw()
    previous = "approval-export"
    for i in range(1, 10):
        node = f"impact-depth-{i}"
        service.store.query(
            "MATCH (a {id:$previous}) CREATE (d:Decision {id:$node,name:$node})-[:DEPENDS_ON {current:true,source:'doc-export-decision-v1'}]->(a)",
            {"previous": previous, "node": node},
            write=True,
        )
        previous = node
    impact = service.store.impact("approval-export")
    assert impact["truncated"] and impact["depth_limit_reached"]
    with pytest.raises(ValueError, match="Impact is incomplete"):
        service.propose()
    assert service.store.actions() == []


def test_inactive_dependency_does_not_propagate_current_impact(service):
    service.store.query(
        "MATCH (:Decision {id:'decision-atlas'})-[r:DEPENDS_ON]->(:Milestone {id:'milestone-export'}) SET r.current=false",
        write=True,
    )
    assert {x["id"] for x in service.store.impact("approval-export")["items"]} == {
        "decision-export",
        "milestone-export",
    }
    assert service.readiness()["status"] == "unknown"


def test_missing_dependency_source_is_visible_and_cannot_create_plan(service):
    service.withdraw()
    service.store.query(
        "MATCH (:Decision {id:'decision-atlas'})-[r:DEPENDS_ON]->(:Milestone {id:'milestone-export'}) SET r.source='doc-missing-v1'",
        write=True,
    )
    result = service.store.impact("approval-export")
    assert result["count"] == 7 and result["sourced"] is False
    assert any(x["evidence_issues"] for x in result["items"])
    with pytest.raises(ValueError, match="evidence is missing"):
        service.propose()
    assert service.store.actions() == []
