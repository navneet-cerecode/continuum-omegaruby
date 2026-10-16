# Actual verification — CONTINUUM / OmegaRuby

Latest local verification: **October 17, 2026 (IST)**. Claims below refer to executed checks, not plans; earlier checkpoints retain their dates and scope.

Latest release verification: **114 tests passed**, real Chrome account/import/paging/company-isolation flows, five live local-model scenarios, a 1,206-node synthetic load experiment and a fresh same-machine archive install. Actual silent demo recordings are supplied; upload remains pending. Original demo records are unchanged. See [RELEASE.md](RELEASE.md) and `artifacts/release-verification.json`. Account mode is implemented and tested but requires administrator provisioning before activation; this is not public production security.

Latest cycle verification: **103 tests passed**; repeated cycles across all three projects, event-time snapshots and legacy reconstruction are covered. Chrome completed two Atlas cycles and historical selection on desktop/mobile; two actual local-agent HTTP calls distinguished an old resolved incident from a current withdrawal without mutation. Free-text historical citations remained weak; this is not general semantic reliability. Original demo records are unchanged. See [CYCLES.md](CYCLES.md) and `artifacts/cycles-verification.json`.

Latest multi-project verification: **90 tests passed**; independent Atlas, Beacon and Orbit lifecycles passed in Chrome on desktop/mobile; real local-agent HTTP calls assessed Beacon/Orbit with their own sources and paths. Original Atlas records survived additive migration. See [MULTI_PROJECT.md](MULTI_PROJECT.md) and `artifacts/multi-project-verification.json`. Earlier checkpoints retain their original scope.

Latest lifecycle verification: **80 tests passed**; the complete withdrawal-to-resolution flow passed in Chrome on desktop/mobile; two genuine local-agent calls explained restored readiness and resolution through HTTP. Original demo actions/history remained unchanged. See [RESTORATION.md](RESTORATION.md) and `artifacts/lifecycle-verification.json`. The normal demo remains withdrawn so the user can perform restoration themselves. The following 66-test checkpoint retains its original scope.

Latest hardening verification: **66 tests passed**, Python and frontend dependency scans report zero known findings, and TypeScript/Vite build passed. Real Chrome checked both the preserved review-required demo and an isolated expired-evidence graph showing unknown readiness, on desktop and mobile, with no page errors or CSP violations. Existing task/change IDs survived policy migration. See [HARDENING.md](HARDENING.md) and `artifacts/hardening-verification.json`. Earlier restart, injection and latency evidence below is retained with its original scope.

## Environment and scope

- Windows 11, Intel Family 6 Model 183 CPU, 20 logical processors, approximately 23.7 GiB physical RAM; NVIDIA GeForce RTX 4060 Laptop GPU available.
- Python 3.12.14; Node 24.12.0; React 19.3.1; Vite 8.3.4; official FalkorDB Python client 1.8.0.
- **Real FalkorDB 4.14.11**, official release module on Redis 8.0.5 in Ubuntu WSL. AOF and RDB files in ignored checkout-local `.runtime/database`.
- Ollama 0.40.4, **installed `llama3:latest` model, ID `365c0bd3c000`**. Local inference, no provider account or API key. Model-selected JSON tools followed by schema-constrained source/path citations and authoritative graph conclusions. This is not native Llama 3 tool calling.
- Seed baseline: **79 nodes, 84 relationships, 24 Markdown sources**, 4 teams, 12 people, 3 projects. Measurements exclude mutation-added plans/actions.

## Executed verification

| Scenario | Actual result |
|---|---|
| Expected impact | Exact seven-ID set equals independently specified `data/expected-impact.json`; Acme and Harbor have five-hop dependency paths |
| Unrelated project exclusion | Beacon and Orbit excluded; adding a non-propagating support relationship does not change impact |
| Graph essential | Removing a relevant DEPENDS_ON relationship changes impact; reversing traversal does not produce downstream commitments |
| Approval withdrawal | Old assumption superseded, new withdrawn assumption and ChangeEvent persisted; repeat withdrawal is idempotent |
| Historical evidence | Original security excerpt remains inspectable; current readiness becomes review_required |
| Ownership | Current register resolves Maya Chen; Ethan Park's old brief and conflict shown; equal-ranked current conflicts abstain |
| Missing evidence | Unknown owner/path remains explicit; absent dependency does not prove safety |
| Cycles and duplicate paths | Eight-hop traversal terminates and impacted IDs are deduplicated |
| Import | Reimport is idempotent and does not restore old approval; changed immutable version rejected; higher version preserves old source history |
| Approval and stale state | Selected tasks persisted with owner/source/target/trigger/proposal links; reapproval does not duplicate; stale revision or supporting edge changes rejected |
| Concurrent approval | Two simultaneous approval requests create one task |
| Completion | Completed follow-up does not restore security approval or resolve the event |
| Fresh session | Fresh Store and fresh browser recover changes/actions from FalkorDB |
| Actual restarts | Database shutdown/restart reloaded AOF; backend process restarted; exact original change/action IDs remained |
| Actual database outage | API returned HTTP 503 with FalkorDB-unavailable message during controlled shutdown; no JSON fallback |
| Model outage and invalid output | Simulated HTTP failures, invalid sources and missing credentials rejected; unavailable local model endpoint returns HTTP 503 without tasks |
| Document injection | Live model retrieved `doc-untrusted-v1`, rejected its instruction as unauthorized; action records unchanged. Tool allowlist has no approval/mutation capability |
| Browser flow | Installed Chrome: UI → API → FalkorDB → UI; both genuine local-agent answers, changed approval, seven impacted items, source conflict, graph-edge evidence, two selected internal tasks and fresh-session recovery |
| Responsive and interaction checks | 1440×1050 desktop and 390×844 mobile; mobile no horizontal overflow; graph edge opens its source; Escape closes evidence drawer; no page errors; observed API calls HTTP 200 |
| Build/configuration | TypeScript check + Vite production build passed; Compose configuration validated |

Automated tests use isolated real FalkorDB graphs. Provider protocol tests are simulated and do not count as live model evidence. See `artifacts/verification.json` for current suite counts and `artifacts/pytest-cycles.xml` for local raw results; earlier XML files retain their checkpoint scope. The latest suite has one Starlette HTTPX TestClient deprecation warning; no test failed.

## Live model evidence

`artifacts/live-agent.json` records two genuine local model runs:

- Before withdrawal: model selected `assess_launch_readiness(project-atlas)`, returned the recorded-readiness conclusion, two full prerequisite paths, five real source version IDs and the ownership conflict. End-to-end time approximately **9.84 s** in the post-hardening isolated run.
- After withdrawal + approved action: model selected `get_open_followups(workspace)`, returned the review-required conclusion, a full graph path, real change/source version IDs and the conflict. End-to-end time approximately **6.26 s**. Structured unresolved actions are rendered separately from model prose.
- Actual injection excerpt: `artifacts/live-injection.json`; model selected `search_company_context`, cited `doc-untrusted-v1`, and rejected its action-approval instruction. Model request time approximately **2.89 s**.

Earlier Llama 3 attempts gave missing/unsupported citations or incomplete loops. They were not counted as passes. Citation requirements were tightened, and local synthesis now constrains source IDs, full paths and graph-computed conclusions. Free-text conflicts/recommendations can still be incomplete or overstated; source/path membership is not proof of natural-language entailment. This small scenario verifies a working agent, not general reliability.

## Measurements

Earlier baseline measurements, before this hardening pass: small fixture, concurrency **1**, warm caches, `perf_counter` wall-clock round trips, seed excluded. Correctness is the exact independently specified expected-ID set, **7/7**. Extra validity/completeness queries have since been added; these numbers are not updated-code benchmarks.

| Measurement | Samples | Warm-ups | Median | p95 |
|---|---:|---:|---:|---:|
| Dependency traversal round trip | 50 | 5 | 0.418 ms | 0.526 ms |
| Complete impact + evidence/owner hydration | 30 | 5 | 22.821 ms | 23.675 ms |

Raw method, machine and range: `artifacts/benchmark.json`. Model latency is separate, as above and in live-run artifacts. No larger synthetic graph or enterprise/concurrent-load benchmark was run. Multiple evidence queries and dense dependency paths are known scaling bottlenecks.

## Evidence and outstanding work

Proof artifacts: browser screenshots 01–08, `browser-verification.json`, `live-agent.json`, `live-injection.json`, `runtime-verification.json`, `benchmark.json`, and final suite summary.

Not verified or completed: complete Docker image build/start on a working Docker Desktop engine; another machine's clean installation; native-tool Ollama/hosted API adapters against live providers; public deployment; public repository publication; demo video upload; participant identity/registration; participant understanding and meaningful contribution sign-off. An actual local demo video was subsequently recorded; a fresh same-machine archive installation passed. These do not establish the remaining external gates.

The current local release demo has already recorded the security withdrawal and two approved tasks. Use a new graph name to rehearse the initial state without deleting history. See README and CONTRIBUTIONS.md.
