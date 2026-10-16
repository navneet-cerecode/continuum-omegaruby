# Hardening pass — CONTINUUM / OmegaRuby

Implemented and verified locally on October 16, 2026. This pass strengthens the local demo's evidence, state and HTTP boundaries. Public deployment still needs authentication and authorization.

This document retains the original hardening checkpoint. Optional account authorization, reviewed batches, pagination and broader local evaluation were subsequently implemented; see [RELEASE.md](RELEASE.md) for current capabilities and limits.

## Findings and fixes

| ID / priority | Finding | Implemented behavior |
|---|---|---|
| H1 / high correctness | A remaining capacity path could support readiness after the security dependency was removed. Source existence alone could also treat expired or non-authoritative evidence as approval. | Projects declare required assumption IDs; assumptions declare required source authority. Missing prerequisites/policy, expired/future/superseded/disputed evidence, missing excerpts/hashes and unresolved owners prevent `supported`. A ticket cannot replace the security review. Historical sources remain inspectable. |
| H2 / high correctness | Bounded traversal could silently omit dependencies. | Readiness fetches 51 paths to detect the 50-path cap. Impact fetches 201 to detect the 200-path cap. Both query for dependencies continuing beyond eight hops. Incomplete readiness is explicit; incomplete impact cannot produce a response plan. Only current dependency edges propagate. |
| H3 / high correctness | Checking only the first two ownership records could miss a third conflicting owner after duplicate records for the same person. | All equally ranked eligible owners must agree. Numeric authority, timezone-aware effective/expiry dates and source validity are checked. Malformed or incomplete current records produce an unresolved owner. |
| H4 / high data integrity | Document imports performed multiple writes and could leave a partially imported document after an invalid subject or conflicting version. | Strict metadata/UTF-8/size validation precedes writes. A single guarded query checks workspace revision, subjects and previous current version before mutation. Version identity is immutable; version number and effective date must increase. Concurrent imports cannot create two current versions through the application. |
| H5 / medium local exposure | Local origin checks did not cover hostile Host headers, cross-site requests lacking Origin, or expensive oversized inputs. | Loopback Host allowlist, cross-site write rejection, 32KB streamed-body limit, JSON-only nonempty mutation bodies, encoded-body rejection, bounded Range headers, CSP and referrer policy. One model investigation per application process; overlapping requests receive 429 and the slot is released on completion/failure. |
| H6 / medium dependency hygiene | The old Starlette version was affected by a file Range request DoS advisory; the audit also identified old pytest and python-dotenv releases. | FastAPI/Starlette and affected pinned dependencies upgraded together. Installed dependency compatibility, real API tests and production UI build pass. Python and frontend audits report zero known findings in the checked locks. |

Implementation: `backend/readiness.py`, `backend/validity.py`, `backend/graph.py`, `backend/importing.py`, `backend/http_guards.py`, `backend/main.py`; UI evidence-gap rendering in `frontend/src/ContextPage.tsx`.

Dependency references: [Starlette Range advisory](https://github.com/Kludex/starlette/security/advisories/GHSA-7f5h-v6xp-fcq8), [python-dotenv advisory](https://github.com/theskumar/python-dotenv/security/advisories/GHSA-mf9w-mj56-hr94). The dotenv advisory concerns write helpers; CONTINUUM uses the read helper, but the dependency was patched. A clean advisory scan is a dated inventory check, not proof of security.

## Executed checks

- **66 tests passed** against real isolated FalkorDB graphs, including missing prerequisites, authoritative-source substitution, expired/future/disputed evidence, traversal caps, third-owner conflicts, invalid/competing imports, stale approvals and HTTP guards. The suite retains simulated provider protocol tests; those are distinct from live inference.
- Two genuine local **Ollama / llama3:latest** runs passed: supported readiness before the update and unresolved follow-ups afterward. No provider account or key is needed. Full source IDs and returned graph paths were validated.
- Installed Chrome tested the preserved demo (`review_required`) and a separate real graph with expired security evidence (`unknown`). Desktop 1440×1050 and mobile 390×844 had no page errors, CSP violations or horizontal overflow. Evidence drawer and Escape dismissal worked. Screenshots were visually inspected.
- Original two action IDs and one change ID match the pre-migration snapshot. Browser checks made no state changes. Only absent fixture policy properties were migrated into the existing demo graph.
- TypeScript check and Vite production build passed; Python dependency compatibility check passed. `pip-audit` and `npm audit` returned zero known dependency findings.

Machine-readable results: `artifacts/hardening-verification.json`, `pytest-hardening.xml`, `hardening-runtime.json`, `browser-hardening.json`, `dependency-audit.json`, `frontend-dependency-audit.json`, and refreshed `live-agent.json`. The one test warning is Starlette's deprecation of its HTTPX TestClient adapter; it does not affect the passing runtime flow.

Reproduce the suite from the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.runtime\pytest-hardening --junitxml=artifacts/pytest-hardening.xml
npm.cmd --prefix frontend run build
.\.venv\Scripts\python.exe scripts\verify-live-agent.py
```

For the read-only browser scenarios, start `scripts/serve-evidence-gap.py` in a separate terminal while the main app runs on 8000, then run `scripts/browser-hardening.cjs` with Playwright available. The temporary server binds to 127.0.0.1:8001 and deletes only its generated graph on normal shutdown. Its HTTP write origins are intentionally not enabled. The standard demo verification script mutates fixture state; do not use it against history you want to preserve.

## Remaining limits

- Local single-company demo; no public login, authorization, tenant isolation or per-user quotas. Host/origin/CSP controls do not replace those. The model semaphore is process-local; use one worker for this local run.
- Source metadata is curated. Valid authority/date/hash metadata does not prove that prose entails a claim. Model citation membership is verified; arbitrary natural-language entailment is not.
- Imports are guarded per document. Full fixture seeding is a trusted multiwrite operation, not an all-or-nothing import batch. This pass does not establish full database rollback guarantees. Racing unmanaged administrator writes is outside the supported application consistency model.
- Eight-hop/path/query budgets deliberately restrict investigations. Cycles or dense graphs may produce conservative incompleteness. General retrieval/history/action pagination remains limited, and larger/concurrent workloads were not benchmarked in this pass.
- CSP permits inline **style attributes** for numeric graph/UI layout, and Google Fonts styles/fonts. Script execution remains restricted to self. The default FastAPI interactive documentation uses CDN scripts that this CSP blocks; use `/openapi.json` for schema inspection.
- The subsequent [restoration implementation](RESTORATION.md) adds replacement evidence and revalidation, with 80 passing tests. Completing a task alone still does not restore approval. Full Docker execution, another-machine installation, public deployment and human contribution sign-off retain their prior verification gaps.
