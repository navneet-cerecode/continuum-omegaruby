"""Strict local Markdown import; one guarded FalkorDB mutation per document."""

import hashlib
import json
from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field, field_validator
from backend.graph import valid_id
from backend.validity import parse_date
from backend.access import actor


class Metadata(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    id: str
    document_id: str
    title: str = Field(min_length=1, max_length=200)
    version: int = Field(ge=1, le=1000000)
    valid_from: str
    authority: str = Field(min_length=1, max_length=80)
    synthetic: bool
    subjects: list[str] = Field(max_length=30)
    supersedes: str | None = None
    relationship_method: str | None = Field(default=None, max_length=300)

    @field_validator("id", "document_id", "supersedes")
    @classmethod
    def identity(cls, value):
        return valid_id(value) if value is not None else None

    @field_validator("valid_from")
    @classmethod
    def date(cls, value):
        return parse_date(value).isoformat().replace("+00:00", "Z")

    @field_validator("synthetic")
    @classmethod
    def fictional(cls, value):
        if value is not True:
            raise ValueError("This demo accepts synthetic sources only")
        return value

    @field_validator("subjects")
    @classmethod
    def subject_ids(cls, value):
        for subject in value:
            valid_id(subject)
        if len(value) != len(set(value)):
            raise ValueError("Duplicate subject IDs")
        return value

    @field_validator("title", "authority")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Blank metadata is not allowed")
        return value


def parse_markdown(path):
    path = Path(path)
    if path.stat().st_size > 64000:
        raise ValueError("Markdown exceeds the 64KB limit")
    raw_bytes = path.read_bytes()
    if len(raw_bytes) > 64000:
        raise ValueError("Markdown exceeds the 64KB limit")
    return parse_bytes(raw_bytes)


def parse_bytes(raw_bytes):
    if len(raw_bytes) > 64000:
        raise ValueError("Markdown exceeds the 64KB limit")
    try:
        raw = raw_bytes.decode("utf-8-sig").replace("\r\n", "\n")
    except UnicodeError as exc:
        raise ValueError("Markdown must be UTF-8") from exc
    if not raw.startswith("---json\n"):
        raise ValueError("Expected Markdown with ---json metadata")
    try:
        header, body = raw[8:].split("\n---\n", 1)
    except ValueError as exc:
        raise ValueError("Missing metadata closing delimiter") from exc
    meta = Metadata.model_validate(json.loads(header)).model_dump(exclude_none=True)
    if meta["id"] == meta["document_id"] or meta["id"] in meta["subjects"]:
        raise ValueError("Source IDs must be distinct from document and subject IDs")
    if not body.strip():
        raise ValueError("A source excerpt is required")
    return meta, body.strip(), hashlib.sha256(raw.encode()).hexdigest()


def optional_entity(store, id):
    rows = store.query(
        "MATCH (n {id:$id}) RETURN properties(n) AS entity, labels(n) AS labels LIMIT 2",
        {"id": id},
    )
    if len(rows) > 1:
        raise ValueError("Duplicate application ID requires repair")
    return {**rows[0]["entity"], "kind": rows[0]["labels"][0]} if rows else None


def import_markdown(store, path):
    return import_source(store, parse_markdown(path))


def import_source(store, parsed, apply=True, expected_revision=None):
    meta, body, digest = parsed
    revision = store.revision()
    if expected_revision is not None and revision != expected_revision:
        raise ValueError("Source preview is stale. Preview again before import")
    existing = optional_entity(store, meta["id"])
    if existing:
        if existing["kind"] != "DocumentVersion":
            raise ValueError("Version ID collides with another entity type")
        if existing.get("sha256"):
            if existing["sha256"] != digest:
                raise ValueError("Version is immutable; create a new version ID")
            return False
    document = optional_entity(store, meta["document_id"])
    if document and document["kind"] != "Document":
        raise ValueError("Document ID collides with another entity type")
    previous = meta.get("supersedes")
    current = store.query(
        "MATCH (v:DocumentVersion)-[:PART_OF]->(d:Document {id:$doc}) WHERE v.current=true RETURN v.id AS id LIMIT 201",
        {"doc": meta["document_id"]},
    )
    other_current = {v["id"] for v in current if v["id"] != meta["id"]}
    if other_current and other_current != {previous}:
        raise ValueError("Import must supersede the sole current document version")
    if previous:
        old = optional_entity(store, previous)
        belongs = store.query(
            "MATCH (v:DocumentVersion {id:$id})-[:PART_OF]->(:Document {id:$doc}) RETURN v.id AS id",
            {"id": previous, "doc": meta["document_id"]},
        )
        if not old or old["kind"] != "DocumentVersion" or not belongs:
            raise ValueError("Superseding versions must belong to the same document")
        if old.get("current") is not True:
            raise ValueError("Cannot supersede a historical version")
        if meta["version"] <= old.get("version", 0) or parse_date(
            meta["valid_from"]
        ) <= parse_date(old.get("valid_from")):
            raise ValueError("Version number and effective date must both increase")
    for subject in meta["subjects"]:
        store.entity(subject)
    if not apply:
        return {
            "metadata": meta,
            "excerpt": body,
            "sha256": digest,
            "revision": revision,
            "already_imported": False,
        }
    # Every precondition precedes every SET/MERGE. Revision CAS handles concurrent app writes.
    rows = store.query(
        """MATCH (w:Workspace {id:'workspace'}) WHERE w.revision=$revision
    OPTIONAL MATCH (present {id:$id})
    WITH w,present WHERE present IS NULL OR (present:DocumentVersion AND present.sha256 IS NULL)
    OPTIONAL MATCH (subject) WHERE subject.id IN $subjects
    WITH w,collect(subject) AS subjects WHERE size(subjects)=size($subjects)
    OPTIONAL MATCH (old:DocumentVersion {id:$previous})
    WITH w,subjects,old WHERE $previous='' OR old.current=true
    MERGE (d:Document {id:$doc}) ON CREATE SET d.name=$title,d.synthetic=true
    MERGE (v:DocumentVersion {id:$id}) SET v.name=$title,v.excerpt=$body,v.sha256=$hash,v.version=$version,v.valid_from=$date,v.authority=$authority,v.current=true,v.synthetic=true,v.classification='confirmed'
    MERGE (v)-[:PART_OF]->(d)
    FOREACH (subject IN subjects | MERGE (subject)-[:SUPPORTED_BY {source:$id}]->(v))
    FOREACH (prior IN CASE WHEN old IS NULL THEN [] ELSE [old] END | SET prior.current=false,prior.valid_to=$date MERGE (v)-[:SUPERSEDES]->(prior))
    SET v.imported_by=$actor,w.revision=w.revision+1 RETURN v.id AS id""",
        {
            "revision": revision,
            "id": meta["id"],
            "doc": meta["document_id"],
            "title": meta["title"],
            "body": body,
            "hash": digest,
            "version": meta["version"],
            "date": meta["valid_from"],
            "authority": meta["authority"],
            "subjects": meta["subjects"],
            "previous": previous or "",
            "actor": actor(),
        },
        write=True,
    )
    if not rows:
        after = optional_entity(store, meta["id"])
        if after and after.get("sha256") == digest:
            return False
        raise ValueError(
            "Graph changed before import. Retry against the latest state; no document was imported."
        )
    return True
