"""Revision-bound keyset pages; graph scope comes only from the authenticated store."""

import base64
import json
from backend.graph import valid_id

KINDS = {
    "history": "ChangeEvent",
    "actions": "ActionItem",
    "plans": "ResponsePlan",
    "restorations": "RestorationReview",
    "sources": "DocumentVersion",
}


def page(store, kind, project_id=None, cursor=None, limit=25):
    if kind not in KINDS or not 1 <= limit <= 100:
        raise ValueError("Unsupported record type or page size")
    if project_id and store.entity(project_id)["kind"] != "Project":
        raise ValueError("Select a project ID")
    revision = store.revision()
    scope = [kind, project_id, store.name, revision]
    at, id = "", ""
    if cursor:
        try:
            data = json.loads(
                base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4))
            )
            if data["scope"] != scope:
                raise ValueError("Scope or graph revision changed; restart browsing")
            at, id = data["at"], valid_id(data["id"])
            if not isinstance(at, str) or len(at) > 80:
                raise ValueError("Invalid cursor timestamp")
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Invalid or stale cursor; restart browsing") from exc
    label = KINDS[kind]
    relation = ""
    if project_id:
        if kind == "history":
            relation = "MATCH (n)-[:AFFECTS]->(:Project {id:$project})"
        elif kind in ("actions", "plans", "restorations"):
            relation = "MATCH (n)-[:TRIGGERED_BY]->(:ChangeEvent)-[:AFFECTS]->(:Project {id:$project})"
        else:
            # Sources can support any entity in a project; expose company sources
            # as a company-wide library instead of pretending this is a complete filter.
            raise ValueError("Source library is company-wide; clear the project filter")
    rows = store.query(
        f"MATCH (n:{label}) {relation} WITH DISTINCT n,coalesce(n.created_at,n.valid_from,'') AS at WHERE ($id='' OR at<$at OR (at=$at AND n.id<$id)) RETURN properties(n) AS record,at ORDER BY at DESC,n.id DESC LIMIT $limit",
        {"project": project_id or "", "id": id, "at": at, "limit": limit + 1},
    )
    more = len(rows) > limit
    rows = rows[:limit]
    for row in rows:
        row["record"].pop("impact_snapshot", None)
    next_cursor = None
    if more:
        last = rows[-1]
        next_cursor = (
            base64.urlsafe_b64encode(
                json.dumps(
                    {"scope": scope, "at": last["at"], "id": last["record"]["id"]}
                ).encode()
            )
            .decode()
            .rstrip("=")
        )
    if store.revision() != revision:
        raise ValueError("Graph changed while reading page; restart browsing")
    return {
        "items": [row["record"] for row in rows],
        "next_cursor": next_cursor,
        "revision": revision,
        "kind": kind,
    }
