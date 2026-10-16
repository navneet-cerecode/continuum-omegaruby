"""Deterministic citation coverage; never label arbitrary prose as entailed."""


def versions(value, result=None):
    result = result if result is not None else {}
    if isinstance(value, dict):
        if isinstance(value.get("id"), str) and isinstance(value.get("excerpt"), str):
            result[value["id"]] = value
        for item in value.values():
            versions(item, result)
    elif isinstance(value, list):
        for item in value:
            versions(item, result)
    return result


def citation_report(answer, evidence):
    sources = versions(evidence)
    selected = {tuple(path) for path in answer.supporting_paths}
    required = set()

    def scan(value):
        if isinstance(value, dict):
            if tuple(value.get("path", [])) in selected:
                required.update(
                    edge["source"]
                    for edge in value.get("edges", [])
                    if edge.get("source")
                )
                required.update(
                    item["id"]
                    for item in value.get("path_evidence", [])
                    if item.get("id")
                )
            for item in value.values():
                scan(item)
        elif isinstance(value, list):
            for item in value:
                scan(item)

    scan(evidence)
    # Assessment source bundles include the approval/withdrawal evidence itself,
    # which may not be the source on a dependency edge.
    for item in evidence:
        if isinstance(item, dict) and item.get("conclusion"):
            required.update(versions(item.get("sources", [])))
    available = required & sources.keys()
    missing = sorted(available - set(answer.source_ids))
    return {
        "model_citation_coverage_complete": not missing
        and not (required - sources.keys()),
        "supplemental_source_ids": missing,
        "unavailable_path_source_ids": sorted(required - sources.keys()),
        "source_excerpts": [
            {
                "id": id,
                "excerpt": sources[id]["excerpt"],
                "reason": "Recorded assessment or selected dependency path",
            }
            for id in sorted(available)
        ],
        "semantic_entailment": "unverified",
        "note": "Supplemental sources are attached by application checks, not chosen by the model. Free-text conflicts and recommendations require human review.",
    }
