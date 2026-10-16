# Local release improvements — October 17, 2026 (IST)

The remaining implementable local work is complete: optional account authentication, server-enforced roles and company graph selection, authenticated reviewer attribution, reviewed Markdown batch onboarding, older-record browsing, stronger source coverage, broader live-model and synthetic-load evaluation, portable setup fixes, CI configuration and an actual recorded demo.

This is a local release candidate, not a claim that arbitrary extraction, semantic entailment or public operations are solved. The original demo remains unchanged and runs in explicit demo mode. Accounts require the administrator to choose a password and enable account mode; no real participant identity has been invented.

## Features and checks

| Area | Implemented and verified scope |
|---|---|
| Accounts | Salted scrypt hashes, opaque HttpOnly/SameSite sessions, CSRF, role checks, bounded sign-in, logout/expiry, account-change revocation and fail-closed configuration. See [ACCESS.md](ACCESS.md). |
| Company separation | Account configuration selects a distinct graph server-side. Parallel requests, identical IDs and cross-company entity access are tested. This is application-level separation; database administrators retain access. |
| Reviewer attribution | Restoration requires the authenticated account's mapped Person ID and the graph's current launch owner. Account names are stored with guarded mutations; prior records remain unattributed. |
| Source onboarding | Human-mapped synthetic Markdown, full preview, explicit confirmation, immutable versions, stale/fingerprint rejection, distinct-document atomic batch publication and idempotence. See [ONBOARDING.md](ONBOARDING.md). |
| Older records | Revision-bound keyset pages for incidents, tasks, plans, reviews and sources; stable ID tie-break; stale scope/revision refusal; browser loads 35 records over two pages. |
| Model support | Readiness now returns actual dependency-source excerpts. Model paths/citations are deduplicated; authoritative tool conclusions are preserved across adapters. Application coverage exposes omitted sources and labels free prose for human review. |
| Automated tests | **114 passed**, no failures/skips, one Starlette HTTPX TestClient deprecation warning. Real isolated FalkorDB plus explicitly simulated provider protocol tests. |
| Browser | Real Chrome exercised sign-in, read-only role denial, CSRF denial, preview/confirmation/import, actor attribution, fresh session and cross-company isolation. Desktop/mobile display checks passed; screenshots inspected. Two complete approval cycles and historical selection were rechecked on a separate owned graph. |
| Model evaluation | Five actual local Ollama scenarios: supported Atlas/Beacon/Orbit, withdrawn Atlas and unaffected Beacon. All five pass tool scope, authoritative conclusion, returned-source coverage and unchanged-state checks. This is a small targeted evaluation, not general semantic reliability. |
| Larger graph | Real graph with **1,206 nodes**, 127 impacted items and 1,000 unrelated records. All 24 runs return the expected set: 12 at concurrency one and 12 at four. Observed medians approximately **263 ms** and **345 ms**, respectively. Small synthetic sample; no enterprise/SLA claim. |
| Setup | Fresh archive extraction, separate Python environment, locked Python install, fresh `npm ci`, production build, 16 API/release tests and actual HTTP backend/UI checks on this same machine. Shared existing WSL database; another-machine and Docker execution remain unverified. |
| Release preparation | Native setup script, one-worker Docker account override/non-root runtime, configuration validation, prepared GitHub Actions workflow, source archive and labeled local demo recording. The GitHub workflow has not run remotely. |

The initial live-model evaluation failed four of five cases because readiness paths lacked their source excerpts. `release-model-eval-initial.json` retains that evidence. The tool was fixed and all five cases rerun. This does not turn source coverage into prose entailment.

Fresh installation exposed optional dependencies with missing versions in the old frontend lockfile. Regeneration from exact package pins added complete version/integrity/platform records; fresh `npm ci` now succeeds. A second clean-checkout run exposed the absent project-local test runtime directory, which setup and tests now create. The final clean-install report records the completed rerun.

## Reviewable artifacts

- `artifacts/release-verification.json`: aggregate of actually executed checks.
- `artifacts/pytest-release.xml`: full raw local suite; excluded from the archive, counts retained in JSON.
- `artifacts/browser-release.json`, `browser-release-display.json`, `browser-release-cycles.json`: browser evidence.
- `artifacts/release-model-eval.json`, `release-agent-ui.json`: real inference and retained traces.
- `artifacts/release-load.json`, `release-clean-install.json`, `release-preserved.json`: performance, clean setup and original-record preservation.
- `artifacts/CONTINUUM-OmegaRuby-demo.mp4`: labeled edit of actual recordings. Silent; workflow playback is slowed for readability. The agent section contains genuine local inference. No participant voice or technical understanding is fabricated.
- `CONTINUUM-OmegaRuby-source.zip`: source, documentation and verification artifacts, excluding credentials, dependencies, runtimes, database files and logs.

## Remaining external and research work

Docker's Linux engine is unavailable on this machine; `docker info` cannot connect to its named pipe. Compose validation passes, but full image build/start is not verified. No Docker reset or unrelated-system change was attempted. Another physical machine is unavailable; the fresh local install is explicitly not a substitute for that check.

The user explicitly authorized publication to [navneet-cerecode/continuum-omegaruby](https://github.com/navneet-cerecode/continuum-omegaruby), with the actual demo attached to a GitHub release. Publication does not submit the hackathon entry. Team registration, member details, contribution log and technical-understanding sign-off are participant-owned. Do not mark them complete on someone else's behalf. [Official rules](https://www.wemakedevs.org/hackathons/falkordb/rules) still require a public repository, working video and meaningful participant contribution; [the schedule](https://www.wemakedevs.org/hackathons/falkordb/schedule) gives **October 18, 2026, 23:59 IST** as the submission deadline, rechecked October 17.

Automatic PDF/Office relationship extraction, general natural-language entailment, externally verified reviewer identity, MFA/recovery, distributed sessions/quotas, infrastructure tenant isolation and production operations remain research/deployment scope. Markdown onboarding is explicitly reviewed and synthetic. Loopback host/origin restrictions remain in force; no public service was exposed.
