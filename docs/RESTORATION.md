# Approval restoration — CONTINUUM / OmegaRuby

Implemented and verified locally on October 16, 2026. Atlas supports withdrawal → response → replacement evidence → explicit revalidation → resolution.

Subsequent extensions support Beacon and Orbit, with project/prerequisite selection and policy-derived authority, then repeated cycles and historical incident selection. See [MULTI_PROJECT.md](MULTI_PROJECT.md) and the latest [103-test checkpoint](CYCLES.md); this Atlas checkpoint retains its original scope.

## Use the workflow

1. Open **Change investigation** after the synthetic withdrawal. Generate and approve any needed tasks.
2. Under **Bring the decision back into review**, enter a replacement security review title, reference and excerpt. Confirm that this fictional review approves the export service, then choose **Record evidence for review**.
3. Inspect the source and projected readiness. Recording evidence creates a pending review; it does not activate approval. Close open event follow-ups in the queue. Rejected tasks count as closed and retain their rejected state.
4. Refresh the review. Check every affected item individually, record a rationale and confirm the synthetic launch-owner role. Items start unchecked.
5. Choose **Revalidate and resolve withdrawal**. This activates the replacement dependency, updates Atlas's prerequisite, retains the old dependency and records reviewer/rationale/targets/resolution. Final launch sign-off remains a separate human decision.

The normal demo graph remains withdrawn with its original two tasks. Verification used isolated graphs; the user's tasks were not completed or resolved.

## Evidence and consistency

`RestorationReview` links to a proposed Assumption, immutable DocumentVersion and triggering ChangeEvent. Replacement evidence is human-entered and **synthetic**, with a stable ID, reference, hash, timestamp and authority metadata. It does not verify real security approval or authenticated identity.

The read-only readiness preview substitutes the candidate at the selected prerequisite endpoint of FalkorDB-returned paths. Prospective paths are explicitly previews, not stored dependencies. Other prerequisite, ownership and evidence checks still apply. Replacement evidence must take effect after the withdrawal; affected dependencies and their sources must be current and valid.

Approval requires the exact affected ID set, current Atlas launch owner, explicit confirmation, rationale, closed follow-ups, complete sourced impact and supported projected readiness. Revision and context fingerprint checks reject stale reviews. One guarded query records replacement dependencies, historical edge validity, updated policy, revalidation and resolution. Identical retries are idempotent; competing reviews cannot resolve the event twice. Unmanaged administrator races retain the existing unsupported-consistency caveat.

New relationships: `PROPOSES` (review → candidate), `RESOLVES` (review → event), `REVALIDATES` (review → affected item), `REVIEWED_BY` (review → synthetic launch owner). Original approval excerpts and follow-up states remain available. Old response plans cannot create new work after resolution.

## Executed verification

- **80 tests passed**, including 14 lifecycle scenarios covering staging without activation, closure, absent withdrawal, invalid evidence, stale/partial/wrong-owner approval, other prerequisite gaps, expired customer dependencies, concurrent/competing reviews and API confirmation. Database tests use real isolated FalkorDB graphs; provider simulations remain separately scoped.
- Chrome completed the browser → API → database flow on desktop and mobile. An open task blocked resolution; seven unchecked items were then individually confirmed. A fresh page recovered supported readiness and resolution. The rationale was inspectable. No page errors, CSP violations or horizontal overflow were observed; screenshots were inspected.
- Two real local **Ollama / llama3:latest** calls through `/api/agent` explained restored readiness and resolved recap, citing replacement evidence and actual paths, without mutating state. This does not establish general language entailment or reliability.
- TypeScript/Vite build passed. Normal demo actions, history and restoration list match their before/after snapshot. Earlier dependency scans and latency measurements retain their original scope.

Proof: `artifacts/lifecycle-verification.json`, `pytest-lifecycle.xml`, `browser-lifecycle.json`, `live-restoration.json`, `lifecycle-preserved-demo.json`, and `lifecycle-*.png`.

## Reproduce and limits

Run `python -m pytest -q --basetemp=.runtime\pytest-lifecycle --junitxml=artifacts/pytest-lifecycle.xml` with the project virtual environment, and `npm.cmd --prefix frontend run build`.

For browser QA, stop the normal backend without deleting/stopping its database, then run `scripts/serve-lifecycle-qa.py` on 8000. Set `PLAYWRIGHT_MODULE` to installed Playwright and run `node scripts/browser-lifecycle.cjs`; it verifies an owned graph marker before mutations. With Ollama configured, run `scripts/verify-live-restoration.py`. Stop the QA server and restart the normal backend with the original `.env`. If termination prevented automatic cleanup, `scripts/serve-lifecycle-qa.py --cleanup` deletes only the generated graph recorded in ignored `.runtime/lifecycle-qa-graph.txt`. Do not overwrite that file while its previous QA server is running.

This checkpoint covers one synthetic Atlas/export-security lifecycle. Multiple curated projects and repeated withdrawal cycles were subsequently implemented; see [CYCLES.md](CYCLES.md). External approval verification, authenticated reviewer identity, per-item owner signatures, general document extraction and public authorization remain future work. Completing a task alone still cannot restore approval.
