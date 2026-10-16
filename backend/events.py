"""Bounded lineage lookup and explicit event-time versus current evidence views."""

import hashlib
import json


def lineage(store, assumption_id):
    assumption = store.entity(assumption_id)
    if assumption["kind"] != "Assumption":
        raise ValueError("Expected an assumption ID")
    if assumption.get("lineage_id"):
        root = store.entity(assumption["lineage_id"])
        if root["kind"] != "Assumption":
            raise ValueError("Invalid prerequisite lineage")
        return root
    roots = store.query(
        "MATCH (:Assumption {id:$id})-[:SUPERSEDES*0..64]->(root:Assumption) OPTIONAL MATCH (root)-[:SUPERSEDES]->(prior:Assumption) WITH root,prior WHERE prior IS NULL RETURN DISTINCT root.id AS id LIMIT 2",
        {"id": assumption_id},
    )
    if len(roots) != 1:
        raise ValueError(
            "Prerequisite lineage is ambiguous or exceeds the legacy lookup bound"
        )
    return store.entity(roots[0]["id"])


def impact(store, event_id, historical=False):
    from backend.changes import context

    scope = context(store, event_id)
    event = scope["event"]
    if not historical:
        return {
            **store.impact(scope["previous"]["id"]),
            "mode": "current",
            "event_id": event_id,
        }
    encoded = event.get("impact_snapshot")
    if encoded:
        if hashlib.sha256(encoded.encode()).hexdigest() != event.get("snapshot_sha256"):
            raise ValueError("Stored incident snapshot failed its integrity check")
        snapshot = json.loads(encoded)
        if (
            not isinstance(snapshot, dict)
            or not isinstance(snapshot.get("items"), list)
            or len(snapshot["items"]) > 200
        ):
            raise ValueError("Stored incident snapshot requires repair")
        return {
            **snapshot,
            "mode": "event_snapshot",
            "event_id": event_id,
            "captured_at": event["created_at"],
            "caveat": "Event-time snapshot: paths, evidence and ownership were recorded at withdrawal. This does not assess current readiness.",
        }
    return {
        **store.impact(scope["previous"]["id"], historical=True),
        "mode": "reconstructed_history",
        "event_id": event_id,
        "caveat": "Legacy incident: reconstructed from retained relationships, not an event-time snapshot. Current source/owner metadata may differ from the withdrawal date.",
    }


def details(store, event_id, project_id=None):
    from backend.changes import context
    from backend.readiness import assess

    scope = context(store, event_id)
    event = scope["event"]
    if project_id:
        allowed = store.query(
            "MATCH (:ChangeEvent {id:$event})-[:AFFECTS]->(:Project {id:$project}) RETURN 1 AS found LIMIT 1",
            {"event": event_id, "project": project_id},
        )
        if not allowed:
            raise ValueError("Incident does not belong to this project")
    resolved = event.get("state") == "resolved"
    project = scope["project"] if project_id is None else store.entity(project_id)
    current_ready = assess(store, project["id"])
    historical = impact(store, event_id, historical=True)
    safe_event = {k: v for k, v in event.items() if k != "impact_snapshot"}
    return {
        "event": safe_event,
        "previous": scope["previous"],
        "withdrawn": scope["withdrawn"],
        "project": project,
        "impact": historical,
        "sources": store.evidence(event_id),
        "actions": [item for item in store.actions() if item["event_id"] == event_id],
        "current_readiness": current_ready,
        "conclusion": (
            "This selected incident is resolved. "
            if resolved
            else "This selected incident remains unresolved. "
        )
        + "Current project readiness is "
        + current_ready["status"]
        + "; historical impact does not establish current approval.",
        "next_step": "Inspect the incident evidence and current prerequisite assessment separately.",
        "historical": True,
        "persisted": True,
    }
