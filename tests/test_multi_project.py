"""Independent project lifecycles use real isolated FalkorDB graphs."""

import pytest
from backend.restoration import record, review, approve
from backend.agent import run_tool
from backend.seed import seed
from test_integration import service
from test_api import client
from test_restoration import confirmation

CASES = [
    (
        "project-atlas",
        "approval-export",
        {
            "decision-export",
            "milestone-export",
            "decision-atlas",
            "milestone-atlas",
            "project-atlas",
            "commitment-acme",
            "commitment-harbor",
        },
    ),
    (
        "project-beacon",
        "approval-beacon",
        {"decision-beacon", "milestone-beacon", "project-beacon"},
    ),
    (
        "project-orbit",
        "approval-orbit",
        {"decision-orbit", "milestone-orbit", "project-orbit"},
    ),
]


def test_shared_prerequisite_checks_every_affected_project(service):
    service.store.query(
        "MATCH (p:Project {id:'project-beacon'}),(a:Assumption {id:'approval-orbit'}) SET p.required_assumptions=['approval-beacon','approval-orbit'] CREATE (p)-[:DEPENDS_ON {current:true,source:'doc-orbit-rollout-v1',classification:'confirmed'}]->(a)",
        write=True,
    )
    event = service.withdraw("project-orbit", "approval-orbit")["event"]["id"]
    service.store.query(
        "MATCH (v:DocumentVersion {id:'doc-beacon-approval-v1'}) SET v.current=false",
        write=True,
    )
    snapshot = replacement(service, event)
    assert snapshot["candidate_readiness"]["status"] == "supported"
    assert not snapshot["can_approve"] and any(
        "Project Beacon" in item for item in snapshot["blockers"]
    )
    with pytest.raises(ValueError):
        approve(service.store, snapshot["review"]["id"], confirmation(snapshot))


def replacement(service, event):
    return record(
        service.store,
        dict(
            event_id=event,
            expected_revision=service.store.revision(),
            title="Synthetic replacement authoritative review",
            reference="REVIEW-2",
            excerpt="The prerequisite was reassessed and is approved for its recorded scope. This is an explicit synthetic approval.",
            synthetic=True,
            approval_confirmed=True,
        ),
    )


@pytest.mark.parametrize("project,prerequisite,expected", CASES)
def test_each_project_full_lifecycle_leaves_other_projects_supported(
    service, project, prerequisite, expected
):
    assert all(service.readiness(p)["status"] == "supported" for p, _, _ in CASES)
    result = service.withdraw(
        project,
        prerequisite,
        service.store.revision(),
        "Synthetic authoritative review withdrew this prerequisite pending revalidation.",
    )
    event = result["event"]["id"]
    assert {item["id"] for item in result["impact"]["items"]} == expected
    assert service.readiness(project)["status"] == "review_required"
    for other, _, _ in CASES:
        if other != project:
            assert service.readiness(other)["status"] == "supported"
            assert service.overview(other)["history"] == []
    plan = service.propose(event)
    assert plan["proposals"] and all(
        item["target"] in expected for item in plan["proposals"]
    )
    service.approve(plan["id"], [item["id"] for item in plan["proposals"]])
    assert all(
        item["event_id"] == event for item in service.overview(project)["actions"]
    )
    for item in service.overview(project)["actions"]:
        service.transition(item["action"]["id"], "completed")
    snapshot = replacement(service, event)
    assert (
        snapshot["source"]["authority"]
        == service.store.entity(prerequisite)["required_evidence_authority"]
    )
    assert snapshot["can_approve"], snapshot["blockers"]
    approve(service.store, snapshot["review"]["id"], confirmation(snapshot))
    assert all(service.readiness(p)["status"] == "supported" for p, _, _ in CASES)
    selected = service.overview(project)
    assert selected["history"][0]["event"]["state"] == "resolved"
    assert selected["context"]["prerequisite_id"] == snapshot["candidate"]["id"]
    assert len(service.recap(project)["changes"]) == 1
    seed(service.store)
    assert service.readiness(project)["status"] == "supported"


def test_cannot_withdraw_another_projects_prerequisite(service):
    rev = service.store.revision()
    with pytest.raises(ValueError, match="not a recorded"):
        service.withdraw(
            "project-beacon",
            "approval-export",
            rev,
            "Synthetic invalid cross-project request must be rejected.",
        )
    assert service.store.revision() == rev and service.store.history() == []


def test_simultaneous_events_do_not_mix_plans_sources_or_recap(service):
    atlas = service.withdraw()["event"]["id"]
    beacon = service.withdraw("project-beacon", "approval-beacon")["event"]["id"]
    atlas_plan = service.propose(atlas)
    beacon_plan = service.propose(beacon)
    assert len(atlas_plan["proposals"]) == 4 and len(beacon_plan["proposals"]) == 1
    assert {item["source"] for item in atlas_plan["proposals"]} != {
        item["source"] for item in beacon_plan["proposals"]
    }
    assert {
        item["event"]["id"] for item in service.recap("project-atlas")["changes"]
    } == {atlas}
    assert {
        item["event"]["id"] for item in service.recap("project-beacon")["changes"]
    } == {beacon}
    assert (
        service.recap("project-orbit")["changes"] == []
        and len(service.recap()["changes"]) == 2
    )
    with pytest.raises(ValueError, match="Selection"):
        service.approve(atlas_plan["id"], [beacon_plan["proposals"][0]["id"]])
    assert service.store.actions() == []


def test_missing_policy_is_unknown_in_selectable_project(service):
    service.store.query(
        "MATCH (p:Project {id:'project-orbit'}) REMOVE p.required_assumptions",
        write=True,
    )
    assert service.readiness("project-orbit")["status"] == "unknown"
    assert service.overview("project-orbit")["prerequisites"] == []


def test_non_security_authority_cannot_be_replaced_with_security(service):
    event = service.withdraw("project-beacon", "approval-beacon")["event"]["id"]
    snapshot = replacement(service, event)
    assert snapshot["source"]["authority"] == "product"
    service.store.query(
        'MATCH (v:DocumentVersion {id:$id}) SET v.authority="security"',
        {"id": snapshot["source"]["id"]},
        write=True,
    )
    snapshot = review(service.store, snapshot["review"]["id"])
    assert not snapshot["can_approve"]
    with pytest.raises(ValueError):
        approve(service.store, snapshot["review"]["id"], confirmation(snapshot))


def test_scoped_agent_tools_do_not_default_to_atlas(service):
    event = service.withdraw("project-orbit", "approval-orbit")["event"]["id"]
    assert (
        run_tool(service, "get_open_followups", {"value": "project-orbit"})["changes"][
            0
        ]["event"]["id"]
        == event
    )
    assert (
        run_tool(service, "get_open_followups", {"value": "project-beacon"})["changes"]
        == []
    )
    preview = run_tool(service, "propose_followup_plan", {"value": event})
    assert {item["id"] for item in preview["impact"]["items"]} == CASES[2][2]
    assert service.store.actions() == []


def test_api_contract_and_stale_revision(client):
    view = client.get("/api/overview?project_id=project-beacon").json()
    assert view["context"]["prerequisite_id"] == "approval-beacon"
    assert (
        client.get("/api/readiness?project_id=project-beacon").json()["status"]
        == "supported"
    )
    body = dict(
        project_id="project-beacon",
        prerequisite_id="approval-beacon",
        expected_revision=view["revision"] - 1,
        reason="Synthetic accessibility review requires a second assessment.",
    )
    assert client.post("/api/changes/withdraw", json=body).status_code == 409
    body["expected_revision"] = view["revision"]
    response = client.post("/api/changes/withdraw", json=body)
    assert response.status_code == 200, response.text
    event = response.json()["event"]["id"]
    assert client.get("/api/overview?project_id=project-atlas").json()["history"] == []
    plan = client.post("/api/plans?event_id=" + event).json()
    assert plan["proposals"][0]["target"] == "decision-beacon"
    assert (
        client.get("/api/recap?project_id=project-beacon").json()["changes"][0][
            "event"
        ]["id"]
        == event
    )
