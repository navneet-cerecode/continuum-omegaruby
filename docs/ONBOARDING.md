# Reviewed source onboarding and record library

Open **Workspace library** in the top bar. Browse incidents, follow-ups, plans, restoration reviews or source versions. Read records in 25-item pages, load older records, and inspect each record's evidence. Incident selection opens the selected project's incident. The library can show company-wide records within the signed-in company's graph; the source library is always company-wide.

Pages sort by timestamp and stable ID with a revision-bound cursor. Timestamp ties do not skip or duplicate IDs. A scope/revision mismatch refuses the cursor and asks you to restart browsing. API clients can request 1–100 items from `/api/records/{kind}`. Cursors are validated query values, not authorization tokens. The main investigation picker remains a recent-100 shortcut; the library supplies older-record access. Recap still refuses a complete resolution conclusion when its bounded history is incomplete.

## Import sources

In demo mode, or with an admin account, choose **Import sources**. Paste Markdown or select one to five `.md` files, up to 24KB combined through the API. The metadata editor's example shows the exact `---json` format: stable version/document IDs, title, version number, effective date, authority, `synthetic:true`, and explicit existing subject IDs. For a new version include `supersedes`; version number and effective date must both increase.

Choose **Preview sources**, inspect every excerpt and mapping, check the confirmation box, then **Import reviewed batch**. Editing content clears the preview. The server revalidates every document, its immutable hash, current version and subjects, then compares the full batch fingerprint and graph revision before one guarded FalkorDB query. Invalid documents or stale previews cannot leave the valid half of a batch imported. Concurrent application requests have one revision winner. Identical already-imported versions are no-ops. One batch permits only one version per distinct document and requires existing subjects; interdependent new entities are refused.

Importing source evidence creates version and support links only. It never creates dependencies, changes an owner, updates project approval policy or resolves a withdrawal. Those remain explicit domain workflows. Source content is untrusted data and is rendered as text. Account-mode imports record the admin account. CLI imports retain their 64KB per-file limit; the HTTP request guard remains 32KB including JSON encoding.

This is human-mapped onboarding for arbitrary **synthetic Markdown content**, not automatic extraction of entities/relationships from PDFs, Office documents or unrestricted company data. Authority metadata is an administrative assertion; it does not prove prose entailment. The hackathon's permitted-data rules still apply. No confidential or private company documents were added.
