"""Readiness needs complete, current, sourced prerequisites; it is not launch sign-off."""

from backend.validity import utc_now, validity_issues, source_issues

PATH_LIMIT = 50
MAX_HOPS = 8


def assess(store, project_id, replacement=None):
    project = store.entity(project_id)
    if project["kind"] != "Project":
        raise ValueError("Readiness requires a project ID")
    revision = store.revision()
    at = utc_now()
    paths = store.query(
        "MATCH p=(n {id:$id})-[:DEPENDS_ON*1..8]->(a:Assumption) WHERE all(r IN relationships(p) WHERE coalesce(r.current,true)=true) RETURN a.id AS assumption_id, properties(a) AS assumption, [v IN nodes(p)|v.id] AS path, [r IN relationships(p)|properties(r)] AS edges LIMIT 51",
        {"id": project_id},
    )
    truncated = len(paths) > PATH_LIMIT
    paths = paths[:PATH_LIMIT]
    # A review preview substitutes only the explicitly proposed prerequisite.
    # Traversal still executes in FalkorDB; no dependency is changed by this read.
    if replacement:
        previous, candidate = replacement
        for path in paths:
            if path["assumption_id"] == previous:
                path["assumption_id"] = candidate["id"]
                path["assumption"] = {**candidate, "state": "approved"}
                path["path"][-1] = candidate["id"]
    boundary = store.query(
        "MATCH p=(n {id:$id})-[:DEPENDS_ON*8]->(a)-[r:DEPENDS_ON]->(b) WHERE all(e IN relationships(p) WHERE coalesce(e.current,true)=true) AND coalesce(r.current,true)=true RETURN a.id AS id LIMIT 1",
        {"id": project_id},
    )
    issues = []

    def issue(code, message, entity_id=None, severity="unknown"):
        item = {"code": code, "message": message, "severity": severity}
        if entity_id:
            item["entity_id"] = entity_id
        if item not in issues:
            issues.append(item)

    if truncated:
        issue(
            "path_limit", "Readiness path limit reached; this assessment is incomplete."
        )
    if boundary:
        issue(
            "depth_limit",
            "Dependencies continue beyond eight hops; this assessment is incomplete.",
        )
    required = project.get("required_assumptions")
    if (
        not isinstance(required, list)
        or not required
        or not all(isinstance(item, str) and item for item in required)
    ):
        required = []
        issue(
            "missing_readiness_policy",
            "Required prerequisites have not been recorded for this project.",
            project_id,
        )
    found = {p["assumption_id"] for p in paths}
    if replacement:
        required = [candidate["id"] if item == previous else item for item in required]
    for missing in sorted(set(required) - found):
        issue(
            "missing_prerequisite",
            f"Required prerequisite {missing} is not reachable through current dependencies.",
            project_id,
        )
    if not paths:
        issue(
            "no_prerequisites",
            "No recorded assumption paths support this assessment.",
            project_id,
        )
    sources = []
    checks = []
    for assumption_id in dict.fromkeys(p["assumption_id"] for p in paths):
        entries = [p for p in paths if p["assumption_id"] == assumption_id]
        assumption = entries[0]["assumption"]
        problems = validity_issues(assumption, at)
        if assumption.get("current") is not True:
            problems.append("not_current")
        if assumption.get("state") not in ("approved", "confirmed"):
            problems.append("unsupported_state")
        review = (
            assumption.get("current") is False
            or assumption.get("state") in ("withdrawn", "rejected", "superseded")
            or assumption.get("classification") == "disputed"
        )
        for problem in dict.fromkeys(problems):
            issue(
                "assumption_" + problem,
                f"{assumption.get('name', assumption_id)}: {problem.replace('_', ' ')}.",
                assumption_id,
                "review_required" if review else "unknown",
            )
        evidence = store.evidence(assumption_id)
        sources.append({"id": assumption_id, "evidence": evidence})
        authority = assumption.get("required_evidence_authority")
        if not authority:
            issue(
                "missing_evidence_policy",
                f"An authoritative source policy is missing for {assumption.get('name', assumption_id)}.",
                assumption_id,
            )
        usable = [
            e
            for e in evidence
            if not source_issues(e["version"], at)
            and authority
            and e["version"].get("authority") == authority
        ]
        if not usable:
            issue(
                "missing_current_evidence",
                f"{assumption.get('name', assumption_id)} has no current, valid source excerpt with provenance.",
                assumption_id,
            )
        checks.append(
            {
                "id": assumption_id,
                "name": assumption.get("name", assumption_id),
                "state": assumption.get("state", "unknown"),
                "assessment": "review_required"
                if review
                else ("unknown" if problems or not usable else "supported"),
            }
        )
    source_cache = {}
    for path in paths:
        for edge in path["edges"]:
            for problem in validity_issues(edge, at):
                issue(
                    "dependency_" + problem,
                    "A dependency on this path is not currently reliable.",
                    path["path"][0],
                )
            source_id = edge.get("source")
            if not source_id:
                issue(
                    "unsourced_dependency",
                    "A dependency has no recorded source version.",
                    project_id,
                )
                continue
            if source_id not in source_cache:
                try:
                    source_cache[source_id] = store.entity(source_id)
                except ValueError:
                    source_cache[source_id] = None
            source = source_cache[source_id]
            if source is None or source_issues(source, at):
                issue(
                    "invalid_dependency_evidence",
                    f"Dependency evidence {source_id} is missing, superseded, unconfirmed, or outside its validity dates.",
                    project_id,
                )
    ownership = store.owners(project_id)
    if ownership["owner"] is None:
        issue(
            "unresolved_owner",
            "Current launch ownership cannot be resolved from valid authoritative evidence.",
            project_id,
            "review_required" if ownership["ambiguous"] else "unknown",
        )
    if store.revision() != revision:
        issue(
            "state_changed",
            "Graph state changed while assembling readiness. Refresh the assessment.",
        )
    status = (
        "review_required"
        if any(i["severity"] == "review_required" for i in issues)
        else ("unknown" if issues else "supported")
    )
    conclusion = {
        "supported": "Recorded prerequisites support launch readiness; final approval remains with the launch lead.",
        "review_required": "Review required; launch is not automatically cancelled.",
        "unknown": "The graph lacks sufficient current, complete evidence to assess launch readiness.",
    }[status]
    return {
        "conclusion": conclusion,
        "status": status,
        "project": project,
        "paths": paths,
        "sources": sources,
        "dependency_sources": [
            source for source in source_cache.values() if source is not None
        ],
        "checks": checks,
        "issues": issues,
        "complete": not truncated and not boundary,
        "truncated": truncated,
        "max_hops": MAX_HOPS,
        "path_limit": PATH_LIMIT,
        "revision": revision,
        "assessed_at": at.isoformat(),
        "owner_resolution": ownership,
        "history": store.history(project_id),
        "next_step": "Inspect prerequisite evidence and confirm operational checks with current owners."
        if status == "supported"
        else "Resolve the listed evidence, ownership, or completeness gaps before making a launch decision.",
        "caveat": "Only recorded prerequisites were assessed; absence of other dependencies does not prove absence of risk.",
    }
