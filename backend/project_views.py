"""Read-only project views over FalkorDB; workspace totals remain explicit."""

from backend.changes import context


def overview(store, project_id=None, prerequisite_id=None, event_id=None):
    from backend.events import lineage, details, impact as event_impact

    data = store.overview()
    if project_id is None:
        if event_id:
            raise ValueError("Select a project when selecting an incident")
        return data
    project = store.entity(project_id)
    if project["kind"] != "Project":
        raise ValueError("Select a project ID")
    prerequisites = []
    policy = project.get("required_assumptions")
    for id in policy if isinstance(policy, list) else []:
        try:
            prerequisites.append(store.entity(id))
        except ValueError:
            pass
    selected = (
        prerequisite_id
        or project.get("primary_assumption_id")
        or project.get("security_prerequisite_id")
        or (prerequisites[0]["id"] if prerequisites else "")
    )
    declared = {item["id"] for item in prerequisites}
    if not prerequisite_id and selected not in declared:
        selected = prerequisites[0]["id"] if prerequisites else ""
    root = lineage(store, selected) if selected else None
    if selected and selected not in declared:
        matches = [
            item
            for item in prerequisites
            if lineage(store, item["id"])["id"] == root["id"]
        ]
        if len(matches) != 1:
            raise ValueError(
                "Prerequisite does not belong to the current project policy"
            )
        selected = matches[0]["id"]
    all_history = store.history(project_id)
    truncated = len(all_history) > 100
    project_history = all_history[:100]
    family = [
        item
        for item in project_history
        if root
        and (
            item["event"].get("lineage_id") == root["id"]
            or item["previous"].get("lineage_id") == root["id"]
            or item["previous"]["id"] == root["id"]
        )
    ]
    if event_id:
        detail = details(store, event_id, project_id)
        row = next(
            (item for item in project_history if item["event"]["id"] == event_id), None
        )
        if row is None:
            row = {
                "event": detail["event"],
                "previous": detail["previous"],
                "created_at": detail["event"]["created_at"],
            }
            project_history.append(row)
        chosen = row
    else:
        active_incidents = [
            item
            for item in family
            if item["previous"]["id"] == selected
            and item["event"].get("state") == "unresolved"
        ]
        approved_incidents = [
            item
            for item in family
            if item["event"].get("restored_assumption_id") == selected
        ]
        chosen = next(iter(active_incidents or approved_incidents or family), None)
    scope = context(store, chosen["event"]["id"]) if chosen else None
    if scope and event_id:
        incident_root = lineage(store, scope["previous"]["id"])
        matches = [
            item
            for item in prerequisites
            if lineage(store, item["id"])["id"] == incident_root["id"]
        ]
        selected = matches[0]["id"] if len(matches) == 1 else ""
    historical = bool(scope and scope["event"].get("state") != "unresolved")
    impact = event_impact(store, scope["event"]["id"], historical) if scope else None
    event_ids = {item["event"]["id"] for item in project_history}
    active = next((item for item in prerequisites if item["id"] == selected), None)
    data.update(
        {
            "history": [chosen] if chosen else [],
            "project_history": project_history,
            "history_truncated": truncated,
            "actions_truncated": len(store.actions(project_id)) > 100,
            "plans_truncated": len(store.plans(project_id)) > 100,
            "prerequisites": prerequisites,
            "impact": impact,
            "actions": [
                item
                for item in store.actions(project_id)
                if item["event_id"] in event_ids
            ],
            "plans": store.plans(project_id),
            "restorations": [
                item
                for item in store.restorations(scope["event"]["id"] if scope else None)
                if scope and item["event_id"] == scope["event"]["id"]
            ],
            "context": {
                "project_id": project_id,
                "prerequisite_id": selected,
                "event_id": scope["event"]["id"] if scope else None,
                "requested_event_id": event_id,
                "historical": historical,
                "can_withdraw": bool(
                    active
                    and active.get("current") is True
                    and active.get("state") in ("approved", "confirmed")
                ),
                "withdrawn_id": scope["withdrawn"]["id"] if scope else None,
                "withdrawal_source_id": scope["source_id"] if scope else None,
                "prerequisite_name": scope["previous"]["name"]
                if scope
                else (active["name"] if active else "No recorded prerequisite"),
                "active_prerequisite_name": active["name"]
                if active
                else "No recorded prerequisite",
            },
        }
    )
    return data


def recap(store, project_id=None):
    from backend.events import impact as event_impact

    if project_id and store.entity(project_id)["kind"] != "Project":
        raise ValueError("Select a project ID")
    history = store.history(project_id)
    history_truncated = len(history) > 100
    history = history[:100]
    ids = {item["event"]["id"] for item in history}
    actions = [item for item in store.actions(project_id) if item["event_id"] in ids]
    scopes = [context(store, item["event"]["id"]) for item in history]
    impacts = [
        event_impact(
            store, item["event"]["id"], item["event"].get("state") == "resolved"
        )
        for item in scopes
    ]
    unresolved_count = sum(item["event"].get("state") != "resolved" for item in history)
    resolved = bool(history) and all(
        item["event"].get("state") == "resolved" for item in history
    )
    legacy = (
        len(history) == 1 and history[0]["event"]["id"] == "change-export-withdrawn"
    )
    conclusion = (
        (
            "Replacement security evidence was approved, affected items were revalidated, and the withdrawal was resolved. Final launch sign-off remains with the launch lead."
            if resolved
            else "Security approval changed; Atlas needs review. Completing a task does not restore approval."
        )
        if legacy
        else (
            "Replacement evidence was approved and affected dependencies were revalidated. The recorded changes are resolved; final sign-off remains a human decision."
            if resolved
            else f"{unresolved_count} of {len(history)} recorded prerequisite change(s) need review. Completing a follow-up alone does not restore approval."
            if history
            else "No recorded approval withdrawal. Review the launch prerequisites."
        )
    )
    return {
        "conclusion": "Incident history is incomplete. A complete resolution status cannot be established from this bounded recap."
        if history_truncated
        else conclusion,
        "history_truncated": history_truncated,
        "changes": history,
        "impact": impacts[0] if impacts else None,
        "impacts": impacts,
        "restorations": [
            item for item in store.restorations() if item["event_id"] in ids
        ],
        "actions": actions,
        "unresolved_actions": [
            item for item in actions if item["action"]["state"] == "approved"
        ],
        "sources": [
            source for item in history for source in store.evidence(item["event"]["id"])
        ],
        "next_step": "Inspect replacement evidence and the revalidation record; final sign-off remains a human decision."
        if resolved
        else "An explicit supporting update is needed to resolve the underlying risk."
        if history
        else "Inspect launch evidence.",
        "project_id": project_id,
        "persisted": True,
    }
