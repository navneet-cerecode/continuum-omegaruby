"""Repeated cycles and historical inspection against real isolated FalkorDB."""

from concurrent.futures import ThreadPoolExecutor
import json
import pytest
from backend.graph import Store
from backend.service import Continuum
from backend.seed import seed
from backend.restoration import record, approve, review
from backend.agent import run_tool
from test_integration import service
from test_api import client
from test_restoration import confirmation


def restore(service, event):
    view = record(
        service.store,
        dict(
            event_id=event,
            expected_revision=service.store.revision(),
            title="Synthetic renewed approval review",
            reference="REVIEW-42",
            excerpt="The recorded prerequisite was reassessed and explicitly approved again for its synthetic reviewed scope.",
            synthetic=True,
            approval_confirmed=True,
        ),
    )
    assert view["can_approve"], view["blockers"]
    body = confirmation(view)
    final = approve(service.store, view["review"]["id"], body)
    return final, body


@pytest.mark.parametrize(
    "project,original,count",
    [
        ("project-atlas", "approval-export", 7),
        ("project-beacon", "approval-beacon", 3),
        ("project-orbit", "approval-orbit", 3),
    ],
)
def test_two_cycles_keep_distinct_events_and_historical_paths(
    service, project, original, count
):
    first = service.withdraw(project, original)["event"]["id"]
    snapshot = service.event_details(first, project)["impact"]
    final, body = restore(service, first)
    replacement = final["candidate"]["id"]
    second = service.withdraw(project, replacement)["event"]
    assert (
        second["id"] != first
        and second["cycle_index"] == 2
        and second["previous_event_id"] == first
    )
    assert second["lineage_id"] == original
    assert service.readiness(project)["status"] == "review_required"
    old = service.overview(project, event_id=first)
    assert old["context"]["historical"] and not old["context"]["can_withdraw"]
    assert old["context"]["prerequisite_id"] == replacement
    assert old["history"][0]["event"]["state"] == "resolved"
    assert old["impact"] == snapshot
    assert old["impact"]["count"] == count and all(
        item["path"][-1] == original for item in old["impact"]["items"]
    )
    assert len(old["project_history"]) == 2
    detail = service.event_details(first, project)
    assert (
        "resolved" in detail["conclusion"]
        and detail["current_readiness"]["status"] == "review_required"
    )
    assert "1 of 2" in service.recap(project)["conclusion"]
    assert approve(service.store, final["review"]["id"], body)["idempotent"]
    assert service.store.entity(second["id"])["state"] == "unresolved"
    last, _ = restore(service, second["id"])
    assert service.readiness(project)["status"] == "supported"
    assert last["candidate"]["id"] != replacement
    assert last["candidate"]["name"] == final["candidate"]["name"], (
        "Names must not grow each cycle"
    )
    assert (
        service.overview(project, original)["context"]["prerequisite_id"]
        == last["candidate"]["id"]
    ), "Old prerequisite URLs resolve to the active approval"
    assert service.event_details(first, project)["impact"] == snapshot
    seed(service.store)
    fresh = Continuum(Store(service.store.name))
    assert (
        fresh.readiness(project)["status"] == "supported"
        and len(fresh.store.history(project)) == 2
    )


def test_tasks_and_stale_restoration_are_separate_across_cycles(service):
    first = service.withdraw()["event"]["id"]
    plan1 = service.propose(first)
    service.approve(plan1["id"], [plan1["proposals"][0]["id"]])
    oldtask = service.store.actions()[0]["action"]["id"]
    service.transition(oldtask, "completed")
    final, _ = restore(service, first)
    second = service.withdraw("project-atlas", final["candidate"]["id"])["event"]["id"]
    plan2 = service.propose(second)
    service.approve(plan2["id"], [plan2["proposals"][0]["id"]])
    assert len(service.store.actions()) == 2
    assert {item["event_id"] for item in service.store.actions()} == {first, second}
    assert service.store.entity(oldtask)["state"] == "completed"
    with pytest.raises(ValueError, match="resolved"):
        service.propose(first)
    with pytest.raises(ValueError):
        service.approve(plan1["id"], [plan1["proposals"][1]["id"]])
    assert service.readiness()["status"] == "review_required"


def test_snapshot_remains_exact_after_topology_and_owner_changes(service):
    first = service.withdraw()["event"]["id"]
    snapshot = service.event_details(first)["impact"]
    restore(service, first)
    service.store.query(
        "MATCH (:Commitment {id:'commitment-acme'})-[r:DEPENDS_ON]->() DELETE r",
        write=True,
    )
    service.store.query(
        "MATCH (:Project {id:'project-atlas'})-[r:OWNED_BY]->() SET r.current=false",
        write=True,
    )
    assert service.event_details(first)["impact"] == snapshot
    assert service.event_details(first)["current_readiness"]["status"] == "unknown"


def test_legacy_event_reconstruction_is_explicit(service):
    event = service.withdraw()["event"]["id"]
    service.store.query(
        "MATCH (e:ChangeEvent {id:$id}) REMOVE e.impact_snapshot,e.snapshot_sha256",
        {"id": event},
        write=True,
    )
    restore(service, event)
    detail = service.event_details(event)
    assert (
        detail["impact"]["mode"] == "reconstructed_history"
        and detail["impact"]["count"] == 7
    )
    assert "not an event-time snapshot" in detail["impact"]["caveat"]


def test_corrupt_snapshot_is_not_silently_reconstructed(service):
    event = service.withdraw()["event"]["id"]
    service.store.query(
        'MATCH (e:ChangeEvent {id:$id}) SET e.impact_snapshot="{}"',
        {"id": event},
        write=True,
    )
    with pytest.raises(ValueError, match="integrity"):
        service.event_details(event)


def test_concurrent_next_cycle_withdrawal_is_idempotent(service):
    first = service.withdraw()["event"]["id"]
    final, _ = restore(service, first)

    def withdraw():
        return Continuum(Store(service.store.name)).withdraw(
            "project-atlas", final["candidate"]["id"]
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: withdraw(), range(2)))
    assert {item["event"]["id"] for item in results}.__len__() == 1
    assert sum(item["created"] for item in results) == 1
    assert len(service.store.history()) == 2
    assert not service.withdraw()["created"], (
        "A retry of the original version does not start a new cycle"
    )


def test_history_selection_rejects_cross_project_and_is_read_only(client):
    event = client.post("/api/changes/withdraw-security").json()["event"]["id"]
    rev = client.get("/api/health").json()["revision"]
    assert (
        client.get(
            "/api/overview", params={"project_id": "project-beacon", "event_id": event}
        ).status_code
        == 409
    )
    assert (
        client.get(
            "/api/events/" + event, params={"project_id": "project-beacon"}
        ).status_code
        == 409
    )
    assert (
        client.get(
            "/api/events/" + event, params={"project_id": "project-atlas"}
        ).json()["impact"]["mode"]
        == "event_snapshot"
    )
    assert client.get("/api/health").json()["revision"] == rev


def test_history_tool_distinguishes_old_resolution_from_current_readiness(service):
    first = service.withdraw()["event"]["id"]
    final, _ = restore(service, first)
    service.withdraw("project-atlas", final["candidate"]["id"])
    result = run_tool(service, "get_change_event", {"value": first})
    assert result["event"]["state"] == "resolved"
    assert result["current_readiness"]["status"] == "review_required"
    assert result["impact"]["mode"] == "event_snapshot"


def test_history_picker_tracks_the_selected_incidents_prerequisite_family(service):
    event = service.withdraw("project-atlas", "assumption-capacity")["event"]["id"]
    final, _ = restore(service, event)
    view = service.overview("project-atlas", "approval-export", event)
    assert view["context"]["prerequisite_id"] == final["candidate"]["id"]
    assert view["context"]["can_withdraw"]
    assert view["history"][0]["previous"]["id"] == "assumption-capacity"


def test_old_pending_review_cannot_resolve_the_next_cycle(service):
    from test_restoration import evidence

    first = service.withdraw()["event"]["id"]
    pending = record(service.store, evidence(service.store.revision(), "PENDING-1"))
    final, _ = restore(service, first)
    second = service.withdraw("project-atlas", final["candidate"]["id"])["event"]["id"]
    old = review(service.store, pending["review"]["id"])
    revision = service.store.revision()
    with pytest.raises(ValueError):
        approve(service.store, old["review"]["id"], confirmation(old))
    assert service.store.revision() == revision
    assert service.store.entity(second)["state"] == "unresolved"


def test_active_cycle_is_selected_even_when_legacy_timestamps_sort_differently(service):
    first = service.withdraw()["event"]["id"]
    final, _ = restore(service, first)
    second = service.withdraw("project-atlas", final["candidate"]["id"])["event"]["id"]
    service.store.query(
        'MATCH (e:ChangeEvent {id:$id}) SET e.created_at="2020-01-01T00:00:00Z"',
        {"id": second},
        write=True,
    )
    assert service.overview("project-atlas")["context"]["event_id"] == second
