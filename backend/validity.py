"""Conservative validity checks for recorded claims, never prose interpretation."""

from datetime import datetime, timezone


def utc_now():
    return datetime.now(timezone.utc)


def parse_date(value):
    if not isinstance(value, str):
        raise ValueError("Expected an ISO date with timezone")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timezone required")
    return parsed.astimezone(timezone.utc)


def validity_issues(record, at):
    issues = []
    if record.get("current") is False:
        issues.append("superseded")
    for field in ("valid_from", "valid_to"):
        if record.get(field):
            try:
                date = parse_date(record[field])
                if field == "valid_from" and date > at:
                    issues.append("not_yet_valid")
                if field == "valid_to" and date <= at:
                    issues.append("expired")
            except (ValueError, TypeError):
                issues.append("invalid_validity_date")
    if record.get("classification") in ("disputed", "inferred", "unknown"):
        issues.append("unconfirmed_claim")
    return issues


def source_issues(source, at):
    issues = validity_issues(source, at)
    if (
        source.get("kind") is not None and source["kind"] != "DocumentVersion"
    ) or source.get("version") is None:
        issues.append("not_a_source_version")
    if source.get("current") is not True:
        issues.append("source_not_current")
    if not isinstance(source.get("excerpt"), str) or not source["excerpt"].strip():
        issues.append("missing_excerpt")
    if not source.get("sha256"):
        issues.append("missing_source_hash")
    if not source.get("authority"):
        issues.append("missing_source_authority")
    if not source.get("valid_from"):
        issues.append("missing_source_date")
    return list(dict.fromkeys(issues))
