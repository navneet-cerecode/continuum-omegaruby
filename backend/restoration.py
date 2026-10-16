"""Explicit synthetic evidence → human review → revalidation; never model-authorized."""

from backend.access import actor

import hashlib
import json
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from typing import Literal
from backend.graph import valid_id
from backend.validity import source_issues, validity_issues, parse_date, utc_now
from backend.readiness import assess

EVENT = "change-export-withdrawn"
PREVIOUS = "approval-export"
PROJECT = "project-atlas"


class ReplacementEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    expected_revision: int = Field(ge=0)
    title: str = Field(min_length=5, max_length=200)
    reference: str = Field(min_length=3, max_length=80)
    excerpt: str = Field(min_length=20, max_length=6000)
    synthetic: Literal[True]
    event_id: str = EVENT
    security_approved: Literal[True] | None = None
    approval_confirmed: Literal[True] | None = None

    @model_validator(mode="after")
    def confirmed(self):
        valid_id(self.event_id)
        if not self.security_approved and not self.approval_confirmed:
            raise ValueError("Explicit replacement approval confirmation is required")
        return self

    @field_validator("title", "reference", "excerpt")
    @classmethod
    def content(cls, value):
        if not value.strip():
            raise ValueError("Evidence cannot be blank")
        return value.strip()


class Revalidation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    expected_revision: int = Field(ge=0)
    fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    reviewer_id: str
    reviewed_targets: list[str] = Field(min_length=1, max_length=200)
    note: str = Field(min_length=10, max_length=2000)
    confirm: Literal[True]

    @field_validator("reviewer_id")
    @classmethod
    def identity(cls, value):
        return valid_id(value)

    @field_validator("reviewed_targets")
    @classmethod
    def targets(cls, value):
        for target in value:
            valid_id(target)
        if len(value) != len(set(value)):
            raise ValueError("Duplicate reviewed targets")
        return value

    @field_validator("note")
    @classmethod
    def rationale(cls, value):
        if len(value.strip()) < 10:
            raise ValueError("Record a revalidation rationale")
        return value.strip()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def record(store, evidence):
    evidence = ReplacementEvidence.model_validate(evidence)
    from backend.changes import context

    scope = context(store, evidence.event_id)
    payload = evidence.model_dump(exclude={"expected_revision"})
    key = digest(payload)[:16]
    legacy = evidence.event_id == EVENT
    review_id = ("restoration-export-" if legacy else "restoration-") + key
    existing = store.query(
        "MATCH (r:RestorationReview {id:$id}) RETURN r.id AS id", {"id": review_id}
    )
    if existing:
        return review(store, review_id)
    event = scope["event"]
    if event.get("state") != "unresolved":
        raise ValueError("Replacement evidence requires an unresolved withdrawal")
    at = utc_now().isoformat()
    source_id = (
        ("doc-security-restoration-" if legacy else "doc-approval-restoration-")
        + key
        + "-v1"
    )
    document_id = source_id.removesuffix("-v1")
    assumption_id = (
        "approval-export-restored-" if legacy else "approval-restored-"
    ) + key
    if not scope["authority"]:
        raise ValueError("The prerequisite has no authority policy")
    from backend.events import lineage

    root = lineage(store, scope["previous"]["id"])
    rows = store.query(
        """MATCH (w:Workspace {id:'workspace'}),(e:ChangeEvent {id:$event})
        WHERE w.revision=$revision AND e.state='unresolved'
        CREATE (d:Document {id:$document,name:$title,synthetic:true})
        CREATE (v:DocumentVersion {id:$source,name:$title,version:1,authority:$authority,valid_from:$at,current:true,classification:'confirmed',synthetic:true,excerpt:$excerpt,sha256:$hash,reference:$reference,origin:'human-entered synthetic replacement review'})
        CREATE (a:Assumption {id:$assumption,name:$name,state:'proposed',current:true,valid_from:$at,required_evidence_authority:$authority,classification:'confirmed',synthetic:true,lineage_id:$lineage})
        CREATE (r:RestorationReview {id:$id,name:'Replacement approval review',state:'pending',created_at:$at,synthetic:true,recorded_by:$actor})
        CREATE (v)-[:PART_OF]->(d),(a)-[:SUPPORTED_BY]->(v),(r)-[:SUPPORTED_BY]->(v),(r)-[:PROPOSES]->(a),(r)-[:TRIGGERED_BY]->(e)
        SET w.revision=w.revision+1 RETURN r.id AS id""",
        {
            "revision": evidence.expected_revision,
            "event": evidence.event_id,
            "authority": scope["authority"],
            "name": "Replacement: " + root["name"],
            "lineage": root["id"],
            "id": review_id,
            "document": document_id,
            "source": source_id,
            "assumption": assumption_id,
            "title": evidence.title,
            "excerpt": evidence.excerpt,
            "hash": digest(payload),
            "reference": evidence.reference,
            "at": at,
            "actor": actor(),
        },
        write=True,
    )
    if not rows:
        if store.query(
            "MATCH (r:RestorationReview {id:$id}) RETURN r.id AS id", {"id": review_id}
        ):
            return review(store, review_id)
        raise ValueError("Stale context: refresh before recording replacement evidence")
    return review(store, review_id)


def review(store, review_id):
    valid_id(review_id)
    revision = store.revision()
    rows = store.query(
        "MATCH (r:RestorationReview {id:$id})-[:PROPOSES]->(a:Assumption) MATCH (r)-[:SUPPORTED_BY]->(v:DocumentVersion) MATCH (r)-[:TRIGGERED_BY]->(e:ChangeEvent) RETURN properties(r) AS review, properties(a) AS candidate, properties(v) AS source, properties(e) AS event",
        {"id": review_id},
    )
    if len(rows) != 1:
        raise ValueError("Replacement review does not exist or requires repair")
    data = rows[0]
    from backend.changes import context

    scope = context(store, data["event"]["id"])
    previous = scope["previous"]["id"]
    resolved = data["review"]["state"] == "approved"
    impact = store.impact(data["candidate"]["id"] if resolved else previous)
    readiness = assess(
        store,
        scope["project"]["id"],
        None if resolved else (previous, data["candidate"]),
    )
    blockers = []
    if not resolved:
        if data["event"]["state"] != "unresolved":
            blockers.append(
                "The withdrawal has already been resolved by another review."
            )
        if data["candidate"].get("state") != "proposed":
            blockers.append("The candidate approval is no longer proposed.")
    if impact["truncated"] or not impact["sourced"] or not impact["items"]:
        blockers.append("Impact is incomplete or missing dependency evidence.")
    if (
        source_issues(data["source"], utc_now())
        or data["source"].get("authority") != scope["authority"]
    ):
        blockers.append(
            "Replacement security evidence is missing, invalid or outside its validity dates."
        )
    try:
        if parse_date(data["source"].get("valid_from")) < parse_date(
            data["event"].get("created_at")
        ):
            blockers.append(
                "Replacement security evidence must take effect after the withdrawal."
            )
    except (ValueError, TypeError):
        blockers.append("Replacement or withdrawal dates require repair.")
    if readiness["status"] != "supported":
        blockers.append(
            "Projected readiness has unresolved prerequisite, source or ownership gaps."
        )
    other_readiness = []
    for item in impact["items"]:
        if item["kind"] == "Project" and item["id"] != scope["project"]["id"]:
            other = assess(
                store, item["id"], None if resolved else (previous, data["candidate"])
            )
            other_readiness.append(
                {k: v for k, v in other.items() if k != "assessed_at"}
            )
            if other["status"] != "supported":
                blockers.append(
                    "Projected readiness is incomplete for " + item["name"] + "."
                )
    for item in impact["items"]:
        if any(validity_issues(edge, utc_now()) for edge in item["edges"]) or any(
            source_issues(source, utc_now()) for source in item["path_evidence"]
        ):
            blockers.append(
                "Dependency evidence is not current and valid for " + item["name"] + "."
            )
        if not item["owner_resolution"]["owner"]:
            blockers.append("Current owner is unresolved for " + item["name"] + ".")
    open_actions = store.query(
        "MATCH (a:ActionItem)-[:TRIGGERED_BY]->(:ChangeEvent {id:$event}) WHERE a.state='approved' RETURN properties(a) AS action ORDER BY a.id",
        {"event": data["event"]["id"]},
    )
    if open_actions:
        blockers.append(
            "Close the event’s open follow-ups before resolving the withdrawal."
        )
    if store.revision() != revision:
        blockers.append("Graph state changed while preparing this review. Refresh it.")
    stable_readiness = {k: v for k, v in readiness.items() if k != "assessed_at"}
    fingerprint = digest(
        {
            "revision": revision,
            "data": data,
            "impact": impact,
            "readiness": stable_readiness,
            "open_actions": open_actions,
            "other_project_readiness": other_readiness,
        }
    )
    return {
        **data,
        "project": scope["project"],
        "previous": scope["previous"],
        "withdrawn": scope["withdrawn"],
        "impact": impact,
        "candidate_readiness": readiness,
        "other_project_readiness": other_readiness,
        "open_actions": open_actions,
        "blockers": blockers,
        "can_approve": not resolved and not blockers,
        "revision": revision,
        "fingerprint": fingerprint,
        "preview_only": not resolved,
    }


def approve(store, review_id, body):
    body = Revalidation.model_validate(body)
    snapshot = review(store, review_id)
    request_hash = digest(body.model_dump())
    if snapshot["review"]["state"] == "approved":
        if snapshot["review"].get("request_hash") != request_hash:
            raise ValueError(
                "This review was already approved with a different selection or rationale"
            )
        return {**snapshot, "idempotent": True}
    if (
        snapshot["revision"] != body.expected_revision
        or snapshot["fingerprint"] != body.fingerprint
    ):
        raise ValueError(
            "Stale replacement review: refresh evidence and revalidate the selection"
        )
    if snapshot["blockers"]:
        raise ValueError("Cannot resolve: " + " ".join(snapshot["blockers"]))
    if set(body.reviewed_targets) != {
        item["id"] for item in snapshot["impact"]["items"]
    }:
        raise ValueError(
            "Explicitly review every affected item; extra or missing selections are refused"
        )
    owner = snapshot["candidate_readiness"]["owner_resolution"]["owner"]
    if not owner or owner["id"] != body.reviewer_id:
        raise ValueError(
            "The synthetic reviewer must be the currently resolved launch owner"
        )
    at = utc_now().isoformat()
    rows = store.query(
        """MATCH (w:Workspace {id:'workspace'}),(r:RestorationReview {id:$review})-[:PROPOSES]->(a:Assumption),
        (r)-[:TRIGGERED_BY]->(e:ChangeEvent),(r)-[:SUPPORTED_BY]->(v:DocumentVersion),
        (old:Assumption {id:$previous}),(withdrawn:Assumption {id:$withdrawn}),
        (p:Project {id:$project}),(owner:Person {id:$owner})
        WHERE w.revision=$revision AND r.state='pending' AND e.state='unresolved'
        MATCH (dependent)-[edge:DEPENDS_ON]->(old) WHERE coalesce(edge.current,true)=true
        WITH w,r,a,e,v,old,withdrawn,p,owner,collect({node:dependent,edge:edge}) AS links
        MATCH (target) WHERE target.id IN $targets
        WITH w,r,a,e,v,old,withdrawn,p,owner,links,collect(target) AS targets WHERE size(targets)=size($targets)
        SET w.revision=w.revision+1,a.state='approved',a.approved_at=$at,
            withdrawn.current=false,withdrawn.state='superseded',withdrawn.valid_to=$at,
            r.state='approved',r.reviewed_at=$at,r.approved_by=$actor,r.reviewer_id=$owner,r.note=$note,r.request_hash=$request_hash,r.reviewed_targets=$targets,
            e.state='resolved',e.resolved_at=$at,e.restoration_review_id=r.id,e.restored_assumption_id=a.id
        CREATE (a)-[:SUPERSEDES]->(withdrawn),(r)-[:RESOLVES]->(e),(r)-[:REVIEWED_BY]->(owner),(e)-[:SUPPORTED_BY]->(v)
        FOREACH (link IN links | FOREACH (dep IN [link.node] | FOREACH (prior IN [link.edge] |
          SET prior.current=false,prior.valid_to=$at
          CREATE (dep)-[next:DEPENDS_ON]->(a)
          SET next += properties(prior),next.id=coalesce(prior.id,'dependency')+'-'+r.id,next.current=true,next.valid_from=$at,next.valid_to=null,next.source=v.id,next.review_id=r.id,next.revalidated_from=old.id)))
        FOREACH (target IN targets | CREATE (r)-[:REVALIDATES]->(target))
        FOREACH (project IN [target IN targets WHERE target:Project] |
          SET project.required_assumptions=[id IN project.required_assumptions | CASE WHEN id=$previous THEN a.id ELSE id END],
              project.primary_assumption_id=CASE WHEN project.primary_assumption_id=$previous THEN a.id ELSE project.primary_assumption_id END,
              project.security_prerequisite_id=CASE WHEN $authority='security' THEN a.id ELSE project.security_prerequisite_id END)
        RETURN r.id AS id""",
        {
            "review": review_id,
            "previous": snapshot["previous"]["id"],
            "withdrawn": snapshot["withdrawn"]["id"],
            "project": snapshot["project"]["id"],
            "authority": snapshot["previous"].get("required_evidence_authority"),
            "revision": body.expected_revision,
            "owner": body.reviewer_id,
            "targets": body.reviewed_targets,
            "note": body.note,
            "request_hash": request_hash,
            "at": at,
            "actor": actor(),
        },
        write=True,
    )
    if not rows:
        raise ValueError("Stale replacement review: no revalidation was applied")
    return {**review(store, review_id), "idempotent": False}
