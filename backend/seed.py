import argparse
import json
from pathlib import Path
from backend.graph import Store, LABELS, RELS, valid_id

ROOT = Path(__file__).resolve().parents[1] / "data"


def fixture_data():
    fixture = json.loads((ROOT / "entities.json").read_text())
    fixture["policies"] = []
    for path in sorted((ROOT / "extensions").glob("*.json")):
        extension = json.loads(path.read_text())
        if extension.get("synthetic") is not True:
            raise ValueError("Only synthetic fixture extensions are supported")
        for key in ("nodes", "edges", "policies"):
            fixture[key].extend(extension.get(key, []))
    return fixture


from backend.importing import parse_markdown, import_markdown


def seed(store):
    store.query(
        "MERGE (w:Workspace {id:'workspace'}) ON CREATE SET w.revision=0,w.name='Northstar Systems',w.synthetic=true",
        write=True,
    )
    fixture = fixture_data()
    for item in fixture["nodes"]:
        kind = item["kind"]
        if kind not in LABELS:
            raise ValueError("Unsupported label")
        props = {k: v for k, v in item.items() if k != "kind"}
        store.query(
            f"MERGE (n:{kind} {{id:$id}}) ON CREATE SET n += $props",
            {"id": valid_id(item["id"]), "props": props},
            write=True,
        )
    for item in fixture["edges"]:
        if item["type"] not in RELS:
            raise ValueError("Unsupported relation")
        props = {k: v for k, v in item.items() if k not in ("from", "to", "type")}
        store.query(
            f"MATCH (a {{id:$a}}),(b {{id:$b}}) MERGE (a)-[r:{item['type']} {{id:$id}}]->(b) ON CREATE SET r += $props",
            {
                "a": valid_id(item["from"]),
                "b": valid_id(item["to"]),
                "id": item["id"],
                "props": props,
            },
            write=True,
        )
    apply_fixture_policies(store, fixture)
    imported = 0
    for file in sorted((ROOT / "documents").glob("*.md")):
        imported += import_markdown(store, file)
    return {"imported_documents": imported, "revision": store.revision()}


def apply_fixture_policies(store, fixture=None):
    """Add absent curated policy fields only; never reset approvals, sources or tasks."""
    fixture = fixture or fixture_data()
    for item in fixture["nodes"] + fixture.get("policies", []):
        for field in (
            "required_assumptions",
            "required_evidence_authority",
            "primary_assumption_id",
            "decision_id",
        ):
            if item.get(field):
                store.query(
                    f"MATCH (w:Workspace {{id:'workspace'}}),(p {{id:$id}}) WHERE p.{field} IS NULL SET p.{field}=$value,w.revision=w.revision+1",
                    {"id": item["id"], "value": item[field]},
                    write=True,
                )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--file",
        help="Import one local synthetic Markdown source; version IDs immutable",
    )
    args = parser.parse_args()
    s = Store()
    print({"imported": import_markdown(s, args.file)} if args.file else seed(s))
