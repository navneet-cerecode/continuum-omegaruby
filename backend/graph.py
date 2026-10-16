"""Reviewed query boundary. FalkorDB is the only organizational state store."""

import os
import re
from time import perf_counter
from dotenv import load_dotenv
from falkordb import FalkorDB
from redis.exceptions import RedisError
from backend.validity import utc_now, parse_date, validity_issues, source_issues

load_dotenv()
LABELS = {
    "Person",
    "Team",
    "Project",
    "Milestone",
    "Document",
    "DocumentVersion",
    "Decision",
    "Assumption",
    "Commitment",
    "ChangeEvent",
    "ActionItem",
    "Workspace",
    "ResponsePlan",
    "ProposedAction",
    "RestorationReview",
}
RELS = {
    "MEMBER_OF",
    "OWNED_BY",
    "PART_OF",
    "DEPENDS_ON",
    "SUPPORTED_BY",
    "RECORDED_IN",
    "SUPERSEDES",
    "AFFECTS",
    "ASSIGNED_TO",
    "TRIGGERED_BY",
    "FOR_DECISION",
    "HAS_PROPOSAL",
    "CREATED_FROM",
    "PROPOSES",
    "RESOLVES",
    "REVALIDATES",
    "REVIEWED_BY",
}


class GraphUnavailable(Exception):
    pass


def valid_id(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[a-z][a-z0-9_-]{0,79}", value):
        raise ValueError("Invalid entity ID")
    return value


class Store:
    def __init__(self, name=None, port=None):
        self.name = name or os.getenv("FALKORDB_GRAPH", "continuum")
        self.port = port or int(os.getenv("FALKORDB_PORT", "6380"))
        self.db = None
        self.graph = None
        self.timings = []

    def query(self, cypher, params=None, write=False):
        start = perf_counter()
        try:
            if self.graph is None:
                self.db = FalkorDB(
                    host=os.getenv("FALKORDB_HOST", "127.0.0.1"),
                    port=self.port,
                    socket_timeout=6,
                    socket_connect_timeout=2,
                )
                self.graph = self.db.select_graph(self.name)
            method = self.graph.query if write else self.graph.ro_query
            result = method(cypher, params or {}, timeout=3000)
            keys = [col[1] for col in result.header]
            return [dict(zip(keys, row)) for row in result.result_set]
        except RedisError as exc:
            # Do not mask query/programming errors as a successful empty result.
            if "Connection" in type(exc).__name__ or "Timeout" in type(exc).__name__:
                self.graph = None
                raise GraphUnavailable(
                    "FalkorDB unavailable; connected context cannot be answered."
                ) from exc
            if "timed out" in str(exc).lower() or "timeout" in str(exc).lower():
                raise GraphUnavailable(
                    "FalkorDB query budget exceeded; investigation incomplete. Narrow the context."
                ) from exc
            raise
        finally:
            self.timings.append(round((perf_counter() - start) * 1000, 3))
            self.timings = self.timings[-1000:]

    def revision(self):
        rows = self.query(
            "MATCH (w:Workspace {id:'workspace'}) RETURN w.revision AS revision"
        )
        if not rows:
            raise ValueError("Graph is not seeded. Run python -m backend.seed")
        return rows[0]["revision"]

    def entity(self, entity_id):
        valid_id(entity_id)
        rows = self.query(
            "MATCH (n {id:$id}) RETURN properties(n) AS entity, labels(n) AS labels LIMIT 2",
            {"id": entity_id},
        )
        if not rows:
            raise ValueError("Entity does not exist")
        if len(rows) > 1:
            raise ValueError("Duplicate application ID requires repair")
        return {**rows[0]["entity"], "kind": rows[0]["labels"][0]}

    def search(self, text):
        return self.query(
            "MATCH (n) WHERE n.name IS NOT NULL AND (toLower(n.name) CONTAINS toLower($q) OR n.id = $q) RETURN properties(n) AS entity, labels(n) AS labels, n.name AS name ORDER BY name LIMIT 30",
            {"q": text[:100]},
        )

    def evidence(self, entity_id):
        valid_id(entity_id)
        # Each dependency and entity points to immutable version IDs.
        return self.query(
            "MATCH (n {id:$id})-[:SUPPORTED_BY|RECORDED_IN]->(v:DocumentVersion)-[:PART_OF]->(d:Document) RETURN properties(v) AS version, properties(d) AS document, v.valid_from AS valid_from ORDER BY valid_from DESC LIMIT 30",
            {"id": entity_id},
        )

    def owners(self, entity_id):
        valid_id(entity_id)
        rows = self.query(
            "MATCH (n {id:$id})-[r:OWNED_BY]->(p:Person) RETURN properties(p) AS person, properties(r) AS record, r.authority AS authority, r.valid_from AS valid_from ORDER BY authority DESC, valid_from DESC LIMIT 201",
            {"id": entity_id},
        )
        complete = len(rows) <= 200
        rows = rows[:200]
        current = []
        problems = []
        sources = []
        source_cache = {}
        at = utc_now()
        for row in rows:
            source = row["record"].get("source")
            if source and source not in source_cache:
                try:
                    source_cache[source] = self.entity(source)
                    sources.append(source_cache[source])
                except ValueError:
                    source_cache[source] = None
            record = row["record"]
            if record.get("current") is not True:
                continue
            validity = validity_issues(record, at)
            if any(p in validity for p in ("expired", "not_yet_valid")):
                continue
            authority = record.get("authority")
            try:
                effective = parse_date(record.get("valid_from"))
            except (ValueError, TypeError):
                validity.append("invalid_effective_date")
                effective = at
            if type(authority) is not int or authority < 0:
                validity.append("invalid_authority")
            evidence = source_cache.get(source)
            if not evidence or source_issues(evidence, at):
                validity.append("invalid_ownership_evidence")
            if validity:
                problems.append(
                    {
                        "person_id": row["person"]["id"],
                        "issues": list(dict.fromkeys(validity)),
                    }
                )
                continue
            current.append((authority, effective, row))
        current.sort(key=lambda item: (item[0], item[1]), reverse=True)
        winner = current[0][2] if current else None
        tied = (
            {item[2]["person"]["id"] for item in current if item[:2] == current[0][:2]}
            if current
            else set()
        )
        ambiguous = len(tied) > 1
        return {
            "owner": None
            if ambiguous or not winner or not complete or problems
            else winner["person"],
            "records": rows,
            "conflict": len({r["person"]["id"] for r in rows}) > 1,
            "ambiguous": ambiguous,
            "sources": sources,
            "complete": complete,
            "issues": problems,
            "policy": "Current, valid, sourced records only; authority descending, then effective time descending. All equal-ranked owners must agree; incomplete or malformed records require review.",
        }

    def impact(self, prerequisite_id, historical=False):
        valid_id(prerequisite_id)
        # Direction: dependent -> prerequisite. Bounded to 8. Only DEPENDS_ON propagates.
        rows = self.query(
            "MATCH p=(n)-[:DEPENDS_ON*1..8]->(a {id:$id}) WHERE (n:Decision OR n:Milestone OR n:Commitment OR n:Project) AND ($historical OR all(r IN relationships(p) WHERE coalesce(r.current,true)=true)) RETURN n.id AS id, n.name AS name, labels(n) AS labels, [v IN nodes(p) | v.id] AS path, [e IN relationships(p) | properties(e)] AS edges, length(p) AS depth ORDER BY depth, id LIMIT 201",
            {"id": prerequisite_id, "historical": historical},
        )
        boundary = self.query(
            "MATCH p=(n)-[:DEPENDS_ON*8]->(a {id:$id}) MATCH (b)-[r:DEPENDS_ON]->(n) WHERE $historical OR (all(e IN relationships(p) WHERE coalesce(e.current,true)=true) AND coalesce(r.current,true)=true) RETURN b.id AS id LIMIT 1",
            {"id": prerequisite_id, "historical": historical},
        )
        path_limit_reached = len(rows) > 200
        truncated = path_limit_reached or bool(boundary)
        unique = {}
        source_cache = {}
        for row in rows[:200]:
            if row["id"] not in unique:
                row["kind"] = row.pop("labels")[0]
                row["owner_resolution"] = self.owners(row["id"])
                row["evidence"] = self.evidence(row["id"])
                row["path_evidence"] = []
                row["evidence_issues"] = []
                for edge in row["edges"]:
                    source_id = edge.get("source")
                    if source_id not in source_cache:
                        try:
                            source_cache[source_id] = self.entity(source_id)
                        except ValueError:
                            source_cache[source_id] = None
                    source = source_cache[source_id]
                    if source and source.get("kind") == "DocumentVersion":
                        row["path_evidence"].append(source)
                    else:
                        row["evidence_issues"].append(
                            {
                                "source_id": source_id,
                                "message": "Dependency source version is missing or invalid.",
                            }
                        )
                unique[row["id"]] = row
        return {
            "items": list(unique.values()),
            "count": len(unique),
            "max_hops": 8,
            "truncated": truncated,
            "path_limit_reached": path_limit_reached,
            "depth_limit_reached": bool(boundary),
            "sourced": not any(item["evidence_issues"] for item in unique.values()),
            "caveat": "Recorded dependencies only. Missing paths do not establish absence of risk. A changed prerequisite requires review; it does not invalidate a decision.",
        }

    def history(self, project_id=None, prerequisite_id=None):
        if project_id:
            valid_id(project_id)
        if prerequisite_id:
            valid_id(prerequisite_id)
        rows = self.query(
            "MATCH (e:ChangeEvent)-[:SUPERSEDES]->(a:Assumption) OPTIONAL MATCH (e)-[:AFFECTS]->(p:Project {id:$project}) WITH DISTINCT e,a,p WHERE ($project='' OR e.project_id=$project OR p IS NOT NULL) AND ($prerequisite='' OR a.id=$prerequisite OR e.restored_assumption_id=$prerequisite) RETURN properties(e) AS event, properties(a) AS previous, e.created_at AS created_at ORDER BY created_at DESC LIMIT 101",
            {"project": project_id or "", "prerequisite": prerequisite_id or ""},
        )
        for row in rows:
            row["event"].pop("impact_snapshot", None)
        return rows

    def actions(self, project_id=None, event_id=None):
        return self.query(
            "MATCH (a:ActionItem)-[:ASSIGNED_TO]->(p:Person) MATCH (a)-[:FOR_DECISION]->(d) MATCH (a)-[:TRIGGERED_BY]->(e:ChangeEvent) OPTIONAL MATCH (e)-[:AFFECTS]->(project:Project {id:$project}) WITH DISTINCT a,p,d,e,project WHERE ($project='' OR project IS NOT NULL) AND ($event='' OR e.id=$event) RETURN properties(a) AS action, p.name AS owner, d.name AS decision, d.id AS target_id, e.id AS event_id, e.name AS trigger, a.created_at AS created_at ORDER BY created_at DESC LIMIT 101",
            {"project": project_id or "", "event": event_id or ""},
        )

    def plans(self, project_id=None):
        return self.query(
            "MATCH (p:ResponsePlan)-[:HAS_PROPOSAL]->(a:ProposedAction) MATCH (p)-[:TRIGGERED_BY]->(e:ChangeEvent) OPTIONAL MATCH (e)-[:AFFECTS]->(project:Project {id:$project}) WITH DISTINCT p,a,e,project WHERE $project='' OR project IS NOT NULL RETURN properties(p) AS plan, e.id AS event_id, p.created_at AS created_at, collect(properties(a)) AS proposals ORDER BY created_at DESC LIMIT 101",
            {"project": project_id or ""},
        )

    def overview(self):
        self.revision()
        counts = self.query(
            "MATCH (n) RETURN labels(n)[0] AS kind, count(n) AS count ORDER BY kind"
        )
        projects = self.query(
            "MATCH (n:Project) RETURN properties(n) AS project, n.name AS name ORDER BY name"
        )
        return {
            "revision": self.revision(),
            "counts": counts,
            "projects": projects,
            "history": self.history(),
            "actions": self.actions(),
            "plans": self.plans(),
            "restorations": self.restorations(),
            "company": "Northstar Systems",
            "synthetic": True,
        }

    def restorations(self, event_id=None):
        return self.query(
            "MATCH (r:RestorationReview)-[:PROPOSES]->(a:Assumption) MATCH (r)-[:SUPPORTED_BY]->(v:DocumentVersion) MATCH (r)-[:TRIGGERED_BY]->(e:ChangeEvent) WHERE $event='' OR e.id=$event RETURN properties(r) AS review, e.id AS event_id, a.id AS assumption_id, v.id AS source_id, r.created_at AS created_at ORDER BY created_at DESC LIMIT 101",
            {"event": event_id or ""},
        )

    def inspect(self, entity_id):
        entity = self.entity(entity_id)
        links = self.query(
            "MATCH (n {id:$id})-[r]-(m) RETURN type(r) AS relation, properties(r) AS edge, properties(m) AS entity, labels(m) AS labels, startNode(r).id AS from_id, endNode(r).id AS to_id LIMIT 40",
            {"id": entity_id},
        )
        return {
            "entity": entity,
            "evidence": self.evidence(entity_id),
            "ownership": self.owners(entity_id),
            "relationships": links,
        }
