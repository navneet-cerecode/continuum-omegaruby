// CONTINUUM — Team OmegaRuby. Values supplied via official-client params.
// Runtime implementations and atomic state mutations: backend/graph.py and backend/service.py.

// Impact direction: dependent -> prerequisite. Only DEPENDS_ON propagates.
MATCH p=(n)-[:DEPENDS_ON*1..8]->(a {id:$id})
WHERE (n:Decision OR n:Milestone OR n:Commitment OR n:Project)
  AND all(r IN relationships(p) WHERE coalesce(r.current,true)=true)
RETURN n.id AS id, n.name AS name, labels(n) AS labels,
       [v IN nodes(p) | v.id] AS path,
       [e IN relationships(p) | properties(e)] AS edges,
       length(p) AS depth
ORDER BY depth, id LIMIT 201;

// The 201st path marks incomplete impact; also check the depth boundary.
MATCH p=(n)-[:DEPENDS_ON*8]->(a {id:$id})
MATCH (b)-[r:DEPENDS_ON]->(n)
WHERE all(e IN relationships(p) WHERE coalesce(e.current,true)=true)
  AND coalesce(r.current,true)=true
RETURN b.id AS id LIMIT 1;

// Immutable historical evidence, deliberately not filtered to current source version.
MATCH (n {id:$id})-[:SUPPORTED_BY|RECORDED_IN]->(v:DocumentVersion)-[:PART_OF]->(d:Document)
RETURN properties(v) AS version, properties(d) AS document, v.valid_from AS valid_from
ORDER BY valid_from DESC LIMIT 30;

// Return conflicts; application validates dates/sources and compares all top-ranked owners.
MATCH (n {id:$id})-[r:OWNED_BY]->(p:Person)
RETURN properties(p) AS person, properties(r) AS record,
       r.authority AS authority, r.valid_from AS valid_from
ORDER BY authority DESC, valid_from DESC LIMIT 201;

// Prerequisites for readiness. Superseded assumptions cannot approve current readiness.
MATCH p=(n {id:$id})-[:DEPENDS_ON*1..8]->(a:Assumption)
WHERE all(r IN relationships(p) WHERE coalesce(r.current,true)=true)
RETURN a.id AS assumption_id, properties(a) AS assumption,
       [v IN nodes(p)|v.id] AS path,
       [r IN relationships(p)|properties(r)] AS edges LIMIT 51;

// The 51st path or a dependency beyond eight hops prevents supported readiness.
// Required prerequisites/source authority are checked in backend/readiness.py.
MATCH p=(n {id:$id})-[:DEPENDS_ON*8]->(a)-[r:DEPENDS_ON]->(b)
WHERE all(e IN relationships(p) WHERE coalesce(e.current,true)=true)
  AND coalesce(r.current,true)=true
RETURN a.id AS id LIMIT 1;

// Decision history and causal change.
MATCH (e:ChangeEvent)-[:SUPERSEDES]->(a:Assumption)
RETURN properties(e) AS event, properties(a) AS previous, e.created_at AS created_at
ORDER BY created_at DESC LIMIT 20;

// Persisted follow-up evidence and assignment.
MATCH (a:ActionItem)-[:ASSIGNED_TO]->(p:Person)
MATCH (a)-[:FOR_DECISION]->(d)
MATCH (a)-[:TRIGGERED_BY]->(e:ChangeEvent)
RETURN properties(a) AS action, p.name AS owner, d.name AS decision,
       e.name AS trigger, a.created_at AS created_at
ORDER BY created_at DESC LIMIT 50;

// Event-time impact snapshot remains queryable independently of current topology.
MATCH (e:ChangeEvent {id:$id})-[:AFFECTS]->(n)
RETURN n.id AS id, labels(n) AS labels, properties(n) AS entity LIMIT 200;

// Current atomic approval uses MATCH workspace revision before MERGE ActionItem.
// See Continuum.approve for full allowlisted query, source/owner/trigger links and idempotency.
