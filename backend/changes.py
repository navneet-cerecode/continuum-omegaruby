"""Project/prerequisite selection and sourced synthetic change recording."""

from backend.access import actor

import hashlib
import json
from pydantic import BaseModel, ConfigDict, Field
from backend.graph import valid_id
from backend.validity import utc_now


class Withdrawal(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    project_id: str
    prerequisite_id: str
    expected_revision: int = Field(ge=0)
    reason: str = Field(min_length=20, max_length=6000)


def context(store, event_id):
    valid_id(event_id)
    rows = store.query(
        "MATCH (e:ChangeEvent {id:$id})-[:SUPERSEDES]->(a:Assumption) RETURN properties(e) AS event,properties(a) AS previous",
        {"id": event_id},
    )
    if len(rows) != 1:
        raise ValueError("Change event does not exist or requires repair")
    data = rows[0]
    projects = store.query(
        "MATCH (:ChangeEvent {id:$id})-[:AFFECTS]->(p:Project) RETURN p.id AS id ORDER BY id",
        {"id": event_id},
    )
    project_id = data["event"].get("project_id") or (
        projects[0]["id"] if projects else None
    )
    if not project_id:
        raise ValueError("Change event has no recorded project scope")
    previous = data["previous"]
    withdrawn = store.entity(
        data["event"].get("withdrawn_assumption_id", previous["id"] + "-withdrawn")
    )
    sources = store.evidence(withdrawn["id"])
    if not sources:
        raise ValueError("Withdrawal has no recorded source")
    return {
        **data,
        "project": store.entity(project_id),
        "withdrawn": withdrawn,
        "source_id": sources[0]["version"]["id"],
        "authority": previous.get("required_evidence_authority"),
    }


def withdraw(
    store,
    project_id="project-atlas",
    prerequisite_id="approval-export",
    expected_revision=None,
    reason=None,
):
    valid_id(project_id)
    valid_id(prerequisite_id)
    project = store.entity(project_id)
    old = store.entity(prerequisite_id)
    if project["kind"] != "Project" or old["kind"] != "Assumption":
        raise ValueError("Select a project and an assumption")
    legacy = project_id == "project-atlas" and prerequisite_id == "approval-export"
    key = hashlib.sha256(prerequisite_id.encode()).hexdigest()[:16]
    event_id = "change-export-withdrawn" if legacy else "change-" + key + "-withdrawn"
    existing = store.query(
        "MATCH (e:ChangeEvent {id:$event})-[:AFFECTS]->(:Project {id:$project}) RETURN e.id AS id",
        {"event": event_id, "project": project_id},
    )
    if existing:
        from backend.events import impact as event_impact

        event = store.entity(event_id)
        return {
            "event": event,
            "created": False,
            "impact": event_impact(store, event_id, event.get("state") == "resolved"),
        }
    paths = store.query(
        "MATCH p=(:Project {id:$project})-[:DEPENDS_ON*1..8]->(:Assumption {id:$id}) WHERE all(r IN relationships(p) WHERE coalesce(r.current,true)=true) RETURN 1 AS found LIMIT 1",
        {"project": project_id, "id": prerequisite_id},
    )
    if not paths or prerequisite_id not in project.get("required_assumptions", []):
        raise ValueError(
            "The prerequisite is not a recorded required dependency of this project"
        )
    if old.get("current") is not True or old.get("state") not in (
        "approved",
        "confirmed",
    ):
        raise ValueError(
            "Only a current approved or confirmed prerequisite can be withdrawn"
        )
    authority = old.get("required_evidence_authority")
    if not isinstance(authority, str) or not authority.strip():
        raise ValueError(
            "A source authority policy is required before recording a change"
        )
    revision = store.revision() if expected_revision is None else expected_revision
    impact = store.impact(prerequisite_id)
    if impact["truncated"] or not impact["sourced"]:
        raise ValueError(
            "Impact is incomplete or unsourced; repair it before recording a change"
        )
    at = utc_now().isoformat()
    source_id = (
        "doc-security-withdrawal-v1"
        if legacy and reason is None
        else "doc-withdrawal-" + key + "-v1"
    )
    reason = reason or (
        "Synthetic update: "
        + old["name"]
        + " is withdrawn pending a new authoritative review."
    )
    if len(reason.strip()) < 20:
        raise ValueError("Record the reason for this synthetic withdrawal")
    from backend.events import lineage

    root = lineage(store, prerequisite_id)
    parents = store.query(
        "MATCH (e:ChangeEvent) WHERE e.restored_assumption_id=$id RETURN e.id AS id,e.cycle_index AS cycle_index LIMIT 2",
        {"id": prerequisite_id},
    )
    if len(parents) > 1:
        raise ValueError("Approval has ambiguous incident lineage")
    previous_event = parents[0]["id"] if parents else None
    cycle = (parents[0].get("cycle_index") or 1) + 1 if parents else 1
    snapshot = json.dumps(impact, sort_keys=True)
    withdrawn_id = (
        prerequisite_id + "-withdrawn"
        if len(prerequisite_id) <= 70
        else "withdrawn-" + key
    )
    rows = store.query(
        """MATCH (w:Workspace {id:'workspace'}),(old:Assumption {id:$previous})
        WHERE w.revision=$revision AND old.current=true AND old.state IN ['approved','confirmed']
        OPTIONAL MATCH (present:ChangeEvent {id:$event}) WITH w,old,present WHERE present IS NULL
        MATCH (target) WHERE target.id IN $targets
        WITH w,old,collect(target) AS targets WHERE size(targets)=size($targets)
        MERGE (d:Document {id:$document}) ON CREATE SET d.name=$name,d.synthetic=true
        MERGE (v:DocumentVersion {id:$source}) ON CREATE SET v.name=$name,v.version=1,v.authority=$authority,v.excerpt=$reason,v.sha256=$hash,v.valid_from=$at,v.current=true,v.synthetic=true,v.classification='confirmed'
        MERGE (v)-[:PART_OF]->(d)
        SET old.current=false,old.state='superseded',old.valid_to=$at,w.revision=w.revision+1
        CREATE (e:ChangeEvent {id:$event,name:$name,created_at:$at,current:true,state:'unresolved',classification:'confirmed',synthetic:true,project_id:$project,prerequisite_id:$previous,withdrawn_assumption_id:$withdrawn,withdrawal_source_id:$source,authority:$authority,lineage_id:$lineage,cycle_index:$cycle,previous_event_id:$parent,impact_snapshot:$snapshot,snapshot_sha256:$snapshot_hash,recorded_by:$actor})
        CREATE (a:Assumption {id:$withdrawn,name:$name,state:'withdrawn',current:true,valid_from:$at,classification:'confirmed',synthetic:true,required_evidence_authority:$authority,lineage_id:$lineage})
        CREATE (e)-[:SUPERSEDES]->(old),(a)-[:SUPERSEDES]->(old),(e)-[:SUPPORTED_BY]->(v),(a)-[:SUPPORTED_BY]->(v),(e)-[:AFFECTS]->(a)
        FOREACH (target IN targets | CREATE (e)-[:AFFECTS]->(target))
        RETURN e.id AS id""",
        {
            "revision": revision,
            "previous": prerequisite_id,
            "targets": [x["id"] for x in impact["items"]],
            "event": event_id,
            "source": source_id,
            "document": source_id.removesuffix("-v1"),
            "project": project_id,
            "withdrawn": withdrawn_id,
            "lineage": root["id"],
            "parent": previous_event,
            "cycle": cycle,
            "snapshot": snapshot,
            "snapshot_hash": hashlib.sha256(snapshot.encode()).hexdigest(),
            "actor": actor(),
            "name": old["name"] + " withdrawn",
            "authority": authority,
            "at": at,
            "reason": reason.strip(),
            "hash": hashlib.sha256(reason.encode()).hexdigest(),
        },
        write=True,
    )
    if not rows:
        if store.query(
            "MATCH (e:ChangeEvent {id:$id}) RETURN e.id AS id", {"id": event_id}
        ):
            return {
                "event": store.entity(event_id),
                "created": False,
                "impact": store.impact(prerequisite_id),
            }
        raise ValueError("Stale context: refresh before recording this change")
    return {
        "event": store.entity(event_id),
        "created": True,
        "impact": store.impact(prerequisite_id),
    }
