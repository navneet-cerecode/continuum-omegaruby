"""Preview human-mapped Markdown; publish a distinct-document batch atomically."""

import hashlib
import json
from pydantic import BaseModel, ConfigDict, Field
from backend.importing import parse_bytes, import_source
from backend.access import actor


class SourceBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    markdown: list[str] = Field(min_length=1, max_length=5)
    expected_revision: int | None = Field(default=None, ge=0)
    fingerprint: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")


def prepare(store, body):
    if sum(len(text.encode("utf-8")) for text in body.markdown) > 24000:
        raise ValueError("Source batch exceeds the 24KB API limit")
    parsed = [parse_bytes(text.encode("utf-8")) for text in body.markdown]
    ids = [item[0]["id"] for item in parsed]
    docs = [item[0]["document_id"] for item in parsed]
    if len(set(ids)) != len(ids) or len(set(docs)) != len(docs) or set(ids) & set(docs):
        raise ValueError(
            "Batch requires distinct source and document IDs; one version per document"
        )
    revision = store.revision()
    previews = []
    for item in parsed:
        result = import_source(store, item, apply=False, expected_revision=revision)
        if result is False:
            result = {
                "metadata": item[0],
                "excerpt": item[1],
                "sha256": item[2],
                "revision": revision,
                "already_imported": True,
            }
        previews.append(result)
    signature = hashlib.sha256(
        json.dumps({"revision": revision, "sources": previews}, sort_keys=True).encode()
    ).hexdigest()
    return {
        "revision": revision,
        "fingerprint": signature,
        "sources": previews,
        "mapping": "Human-selected existing subject IDs. No dependency or ownership relationships are inferred.",
    }


def publish(store, body):
    preview = prepare(store, body)
    if (
        body.expected_revision != preview["revision"]
        or body.fingerprint != preview["fingerprint"]
    ):
        raise ValueError("Source preview changed; preview the full batch again")
    items = []
    for item in preview["sources"]:
        if item["already_imported"]:
            continue
        meta = item["metadata"]
        items.append(
            {
                **meta,
                "body": item["excerpt"],
                "hash": item["sha256"],
                "previous": meta.get("supersedes", ""),
            }
        )
    if not items:
        return {"imported": 0, "revision": preview["revision"], "ids": []}
    # All document validation and workspace CAS precede writes. Batch subjects
    # must already exist; interdependent new subjects are deliberately refused.
    rows = store.query(
        """MATCH (w:Workspace {id:'workspace'}) WHERE w.revision=$revision
    WITH w UNWIND $items AS item
    MERGE (d:Document {id:item.document_id}) ON CREATE SET d.name=item.title,d.synthetic=true
    MERGE (v:DocumentVersion {id:item.id}) SET v.name=item.title,v.excerpt=item.body,v.sha256=item.hash,v.version=item.version,v.valid_from=item.valid_from,v.authority=item.authority,v.current=true,v.synthetic=true,v.classification='confirmed',v.imported_by=$actor
    CREATE (v)-[:PART_OF]->(d)
    WITH w,item,v OPTIONAL MATCH (old:DocumentVersion {id:item.previous})
    FOREACH (prior IN CASE WHEN old IS NULL THEN [] ELSE [old] END | SET prior.current=false,prior.valid_to=item.valid_from CREATE (v)-[:SUPERSEDES]->(prior))
    WITH w,item,v OPTIONAL MATCH (subject) WHERE subject.id IN item.subjects
    WITH w,item,v,collect(subject) AS subjects
    FOREACH (s IN subjects | MERGE (s)-[:SUPPORTED_BY {source:item.id}]->(v))
    WITH DISTINCT w SET w.revision=w.revision+1 RETURN w.revision AS revision""",
        {"revision": preview["revision"], "items": items, "actor": actor()},
        write=True,
    )
    if not rows:
        raise ValueError("Graph changed before batch import; no source was imported")
    return {
        "imported": len(items),
        "revision": rows[0]["revision"],
        "ids": [item["id"] for item in items],
    }
