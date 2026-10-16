# Repeated approval cycles — CONTINUUM / OmegaRuby

Implemented and verified locally on **October 17, 2026 (IST)**. Atlas, Beacon and Orbit support repeated withdrawal → response → replacement evidence → explicit revalidation cycles. Each cycle retains its own incident, tasks, review, evidence and resolution.

## Use the workflow

After restoring a prerequisite, choose **Record another update** to withdraw its current replacement approval. Complete the same evidence and revalidation workflow again. Completing a follow-up still cannot restore approval.

Use **Incident history** to inspect an earlier cycle. Selection persists in the URL and survives a fresh page. Changing project or prerequisite clears the explicit incident selection. The default selection follows the current prerequisite's incident. An old prerequisite URL resolves to the family's current approval; selecting an incident from another prerequisite family also updates the prerequisite selector.

An older resolved incident shows its historical dependency paths, evidence and resolution. Snapshot ownership is labeled **Owner at withdrawal**. Current project readiness and current responsibility are shown separately. An old resolution does not establish current approval, and resolved incidents expose no controls to generate or approve another response. Selecting history never changes the active prerequisite. Agent questions receive the explicitly selected incident ID through a read-only typed tool.

## Stored history and boundaries

New ChangeEvents store `lineage_id`, `cycle_index`, `previous_event_id`, an impact snapshot and `snapshot_sha256` in FalkorDB. Replacement assumptions retain the same root lineage. Event-specific evidence/review IDs prevent cross-cycle collisions; replacement names stay stable. Old request retries return their original incident rather than creating another cycle. Revision and context checks still guard writes, and old plans/reviews cannot resolve a later withdrawal.

The snapshot captures paths, edge evidence, sources and ownership at withdrawal. Its SHA-256 checksum detects inconsistent stored payloads; it is **not a signature or protection against an administrator who can rewrite both fields**. Corrupt snapshots fail explicitly. Current unresolved investigations still recompute live impact; historical resolved investigations use their stored snapshot.

Legacy incidents without snapshots are labeled **reconstructed history**, using retained dependency edges and current metadata. They are not represented as event-time evidence. The original demo incident is intentionally left in this category. Legacy root discovery is bounded to 64 supersession hops; failure to establish a unique root blocks a new cycle. Cached root IDs support subsequent cycles without walking the full lineage.

The picker lists the latest 100 project incidents and discloses truncation. An older known incident ID remains accessible through `/api/events/{event_id}?project_id=...` or an explicit `event` URL parameter. Workspace recap discloses a truncated history and refuses to conclude that all incidents are resolved. This is bounded history access, not general pagination. Project filters are not authorization.

## Executed verification

- **103 tests passed**, with no failures or skips and one Starlette HTTPX TestClient deprecation warning. Real isolated FalkorDB tests complete two cycles for each of Atlas, Beacon and Orbit and cover independent tasks/reviews, concurrency, idempotent retries, stale reviews, reseeding, legacy reconstruction, topology/ownership changes, checksum failure, cross-project refusal and historical agent context.
- Installed Chrome completed two Atlas cycles through UI → API → real FalkorDB. While the second withdrawal was unresolved, selecting cycle one kept its snapshot unchanged, displayed current readiness as `review_required`, and exposed no resolved-incident mutation controls. Fresh-page selection and desktop/mobile layouts passed without page errors, CSP violations or horizontal overflow. Final production-build labels were checked separately and screenshots inspected.
- Two actual local **Ollama / llama3:latest** HTTP runs compared the first resolved incident with a third unresolved withdrawal in the same isolated graph. The historical tool returned the old path and an explicit current-review-required conclusion; the current readiness tool also required review. Recorded times were approximately 12.88 s and 5.82 s. Model calls left state unchanged. Historical prose selected only ownership citations, repeated a path and produced a weak conflict description: source/path membership and deterministic conclusions passed, but these runs do not establish semantic entailment or general model reliability.
- TypeScript/Vite production build passed. The original demo graph remains at revision 40: Atlas `review_required`, Beacon and Orbit `supported`. Original actions, history and restoration records match their before/after snapshot. Only owned QA graphs were cleaned up.

Proof: `artifacts/cycles-verification.json`, `pytest-cycles.xml`, `browser-cycles.json`, `browser-cycles-display.json`, `live-cycles.json`, `cycles-preserved.json` and `cycles-*-desktop/mobile.png`. Raw pytest XML stays local and is excluded from the source archive; the JSON report records its counts and duration.

## Reproduce and remaining scope

Run `python -m pytest -q --basetemp=.runtime\pytest-cycles --junitxml=artifacts/pytest-cycles.xml` with the project environment, then `npm.cmd --prefix frontend run build`.

For browser/model QA, follow [RESTORATION.md](RESTORATION.md)'s owned test-server setup. Set `PLAYWRIGHT_MODULE` to installed Playwright, run `node scripts/browser-cycles.cjs`, then `python scripts/verify-live-cycles.py` against that same graph. `node scripts/browser-cycles.cjs --display-only` checks the final labels after the live script creates its third test withdrawal. Clean up the owned graph and restart the normal backend afterward. Do not run these mutation scripts against a user's graph.

The subsequent [release checkpoint](RELEASE.md) adds reviewed Markdown onboarding, optional account/reviewer/company access, record pagination, targeted evidence and load evaluation, fresh same-machine setup and an actual video. Automatic arbitrary-document extraction, general semantic entailment, public operations, Docker execution and another-machine installation remain unfinished. Publication/upload, registration and human contribution sign-off remain separate release activities.
