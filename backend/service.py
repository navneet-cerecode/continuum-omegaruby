from backend.access import actor
import hashlib
import json
from datetime import datetime, timezone


def now():
    return datetime.now(timezone.utc).isoformat()


class Continuum:
    def __init__(self, store):
        self.store = store

    def readiness(self, project_id="project-atlas"):
        from backend.readiness import assess

        return assess(self.store, project_id)

    def withdraw(
        self,
        project_id="project-atlas",
        prerequisite_id="approval-export",
        expected_revision=None,
        reason=None,
    ):
        from backend.changes import withdraw

        return withdraw(
            self.store, project_id, prerequisite_id, expected_revision, reason
        )

    def propose(self, event_id="change-export-withdrawn"):
        from backend.changes import context

        scope = context(self.store, event_id)
        event = scope["event"]
        if event.get("state") != "unresolved":
            raise ValueError(
                "This withdrawal is resolved; its historical response plans cannot create new work"
            )
        revision = self.store.revision()
        impact = self.store.impact(scope["previous"]["id"])
        if impact["truncated"]:
            raise ValueError(
                "Impact is incomplete; narrow or repair the graph before proposing follow-ups"
            )
        if not impact.get("sourced", True):
            raise ValueError(
                "Dependency evidence is missing; repair the source links before proposing follow-ups"
            )
        fingerprint = hashlib.sha256(
            json.dumps(impact, sort_keys=True).encode()
        ).hexdigest()
        recorded_targets = {
            x["target_id"] for x in self.store.actions() if x["event_id"] == event_id
        }
        candidates = [
            x
            for x in impact["items"]
            if x["kind"] in ("Decision", "Commitment")
            and x["id"] not in recorded_targets
        ]
        proposals = []
        for item in candidates:
            owner = item["owner_resolution"]["owner"]
            if owner:
                proposals.append(
                    {
                        "id": f"proposal-{revision}-{fingerprint[:8]}-{item['id']}",
                        "name": f"Review {item['name']}",
                        "target": item["id"],
                        "owner": owner["id"],
                        "state": "proposed",
                        "reason": scope["previous"]["name"]
                        + " supporting this dependency was withdrawn.",
                        "source": scope["source_id"],
                    }
                )
        plan_id = f"plan-{event_id}-{revision}-{fingerprint[:8]}"
        draft = (
            "INTERNAL DRAFT — NOT SENT\n"
            + scope["previous"]["name"]
            + " has been withdrawn. "
            + scope["project"]["name"]
            + " and recorded downstream dependencies need review. Current owners: "
            + ", ".join(
                sorted(
                    {
                        x["owner_resolution"]["owner"]["name"]
                        for x in candidates
                        if x["owner_resolution"]["owner"]
                    }
                )
            )
            + ". No launch cancellation or customer notification is authorized by this draft."
        )
        rows = self.store.query(
            """MATCH (w:Workspace {id:'workspace'}), (e:ChangeEvent {id:$event}) WHERE w.revision=$revision
        MERGE (p:ResponsePlan {id:$id}) ON CREATE SET p.name='Review response plan',p.revision=$revision,p.created_at=$at,p.draft=$draft,p.fingerprint=$fingerprint
        MERGE (p)-[:TRIGGERED_BY]->(e)
        WITH p UNWIND $items AS item
        MERGE (a:ProposedAction {id:item.id}) ON CREATE SET a += item
        MERGE (p)-[:HAS_PROPOSAL]->(a)
        RETURN p.id AS id""",
            {
                "event": event_id,
                "revision": revision,
                "id": plan_id,
                "at": now(),
                "draft": draft,
                "items": proposals,
                "fingerprint": fingerprint,
            },
            write=True,
        )
        if proposals and not rows:
            raise ValueError("Graph changed while planning; investigate again")
        return {
            "id": plan_id,
            "revision": revision,
            "proposals": proposals,
            "draft": draft,
            "impact": impact,
            "event": event,
            "missing_owners": [
                x["id"] for x in candidates if not x["owner_resolution"]["owner"]
            ],
        }

    def approve(self, plan_id, selected):
        if not selected:
            raise ValueError("Select at least one proposal")
        from backend.graph import valid_id

        valid_id(plan_id)
        for item in selected:
            valid_id(item)
        rows = self.store.query(
            """MATCH (w:Workspace {id:'workspace'}), (p:ResponsePlan {id:$plan})-[:HAS_PROPOSAL]->(a:ProposedAction)
        WHERE a.id IN $selected RETURN properties(a) AS proposal, p.revision AS revision""",
            {"plan": plan_id, "selected": selected},
        )
        if len(rows) != len(set(selected)):
            raise ValueError("Selection does not belong to this plan")
        # Idempotent retry of the same approved selection succeeds even after revision advance.
        existing = self.store.query(
            "MATCH (a:ActionItem) WHERE a.proposal_id IN $selected RETURN a.proposal_id AS id",
            {"selected": selected},
        )
        if {x["id"] for x in existing} == set(selected) or all(
            x["proposal"].get("state") == "approved" for x in rows
        ):
            return {"actions": self.store.actions(), "created": 0, "idempotent": True}
        persisted_plan = self.store.entity(plan_id)
        from backend.changes import context

        events = self.store.query(
            "MATCH (:ResponsePlan {id:$id})-[:TRIGGERED_BY]->(e:ChangeEvent) RETURN e.id AS id",
            {"id": plan_id},
        )
        if len(events) != 1:
            raise ValueError("Response plan has no unique triggering event")
        scope = context(self.store, events[0]["id"])
        if scope["event"].get("state") != "unresolved":
            raise ValueError(
                "This withdrawal is resolved; no further tasks may be approved"
            )
        fingerprint = hashlib.sha256(
            json.dumps(
                self.store.impact(scope["previous"]["id"]), sort_keys=True
            ).encode()
        ).hexdigest()
        if persisted_plan.get("fingerprint") != fingerprint:
            raise ValueError(
                "Stale proposal: supporting paths, evidence or ownership changed. Generate a fresh plan."
            )
        # Compare-and-set inside the atomic graph mutation prevents concurrent stale approvals.
        revision = rows[0]["revision"]
        result = self.store.query(
            """MATCH (w:Workspace {id:'workspace'}), (p:ResponsePlan {id:$plan})-[:TRIGGERED_BY]->(e:ChangeEvent)
        WHERE w.revision=$revision
        SET w.revision=w.revision+1
        WITH w,p,e MATCH (p)-[:HAS_PROPOSAL]->(a:ProposedAction) WHERE a.id IN $selected
        MATCH (owner:Person {id:a.owner}), (target {id:a.target}), (v:DocumentVersion {id:a.source})
        MERGE (task:ActionItem {id:'action-'+e.id+'-'+a.target}) ON CREATE SET task.name=a.name,task.state='approved',task.created_at=$at,task.proposal_id=a.id,task.classification='confirmed',task.approved_by=$actor
        SET a.state='approved'
        MERGE (task)-[:ASSIGNED_TO]->(owner) MERGE (task)-[:FOR_DECISION]->(target)
        MERGE (task)-[:TRIGGERED_BY]->(e) MERGE (task)-[:SUPPORTED_BY]->(v) MERGE (task)-[:CREATED_FROM]->(a)
        RETURN task.id AS id""",
            {
                "plan": plan_id,
                "selected": selected,
                "revision": revision,
                "at": now(),
                "actor": actor(),
            },
            write=True,
        )
        if not result:
            raise ValueError(
                "Stale proposal: graph state changed. Generate a fresh plan before approval."
            )
        return {
            "actions": self.store.actions(),
            "created": len(result),
            "idempotent": False,
        }

    def transition(self, action_id, state):
        if state not in ("completed", "rejected"):
            raise ValueError("Unsupported action state")
        task = self.store.entity(action_id)
        if task.get("state") == state:
            return task
        if task.get("state") != "approved":
            raise ValueError("Only approved tasks may be completed or rejected")
        rows = self.store.query(
            "MATCH (w:Workspace {id:'workspace'}),(a:ActionItem {id:$id}) WHERE a.state='approved' SET a.state=$state,a.updated_at=$at,a.updated_by=$actor,w.revision=w.revision+1 RETURN properties(a) AS action",
            {"id": action_id, "state": state, "at": now(), "actor": actor()},
            write=True,
        )
        if not rows:
            raise ValueError("Action changed concurrently")
        return rows[0]["action"]

    def overview(self, project_id=None, prerequisite_id=None, event_id=None):
        from backend.project_views import overview

        return overview(self.store, project_id, prerequisite_id, event_id)

    def event_details(self, event_id, project_id=None):
        from backend.events import details

        return details(self.store, event_id, project_id)

    def recap(self, project_id=None):
        from backend.project_views import recap

        return recap(self.store, project_id)
