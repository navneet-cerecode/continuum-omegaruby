# Multi-project workflows — CONTINUUM / OmegaRuby

Implemented and verified locally on October 16, 2026. Project and prerequisite selectors scope readiness, investigation, plans, follow-up queues, replacement evidence and agent questions.

## Use it

Choose Atlas, Beacon or Orbit from **Project**, then a recorded **Prerequisite**. Readiness assesses all required prerequisites for that project; the selected prerequisite controls the investigation. Introduce a synthetic update, generate/approve internal tasks, record replacement evidence, close open event tasks, refresh the review and explicitly confirm each affected item with a rationale. Revalidation restores the dependency and resolves that event; final operational sign-off remains human-controlled.

Selection persists in the URL and survives a fresh page. Switching scope clears cached plans, task selections, evidence and review controls. The queue shows the selected project's tasks with their event links. Investigation/restoration follow the selected prerequisite's latest event. Workspace totals remain company-wide. Agent questions and deterministic recap receive the selected project ID; workspace tools remain available for explicitly broader questions.

## Disclosed fixture extension

Original source versions were not rewritten. `data/extensions/multi-project.json` and two new synthetic documents explicitly add Beacon decision/milestone accountability by fictional Sofia Reyes (`beacon-owners.md`), and Orbit controls, decision, pilot milestone, independent dependencies and Leah Ortiz's accountability (`orbit-rollout.md`). These are curated fictional additions, not extracted facts. Only absent selection/policy fields are added to existing projects.

The fixture has **26 Markdown sources**. Atlas's original impact remains seven items; Beacon and Orbit each have three independent impacted items. Required source authority comes from each prerequisite: Security for Atlas exports, Product for Beacon accessibility, Platform for Orbit controls. A different authority cannot substitute for the required one.

## State boundaries

Change recording validates required-project membership, sourced bounded impact and revision before writing a synthetic withdrawal source, supersession and affected-item snapshot. Plans and approvals resolve their actual event. Original Atlas routes/defaults remain compatible.

Restoration derives project, prerequisite, withdrawn assumption and authority from stored links. Revision, fingerprint, completeness, source dates, current owners, closed event tasks and explicit item confirmation remain required. Shared prerequisites retain global impact: every affected project's projected readiness must pass, and matching policies update together. Project selection is a view filter, not public authorization.

## Executed verification

- **90 tests passed**, including complete independent lifecycles, unrelated-project exclusion, simultaneous events without mixed plans/sources, invalid cross-project selection, missing policy, authority mismatch, scoped agent tools, stale API revision and shared-prerequisite readiness blocking. The prior 80 tests remain included.
- Installed Chrome completed all three withdrawal → task → evidence → revalidation → resolution flows against real isolated FalkorDB. Other projects stayed supported; tasks stayed with their event. A fresh page recovered Beacon selection/resolution. Desktop/mobile checks found no page errors, CSP violations or horizontal overflow. The final build was also checked read-only; screenshots were inspected.
- Two actual local **Ollama / llama3:latest** HTTP investigations assessed restored Beacon and Orbit using their own project IDs, replacement sources and graph paths, without state changes. Recorded times: approximately 13.20 s and 3.95 s; these are observations, not a benchmark or general reliability guarantee.
- TypeScript/Vite build passed. Additive migration imported two new source documents. Original Atlas action records, event history and restoration list match the before/after snapshot. Normal demo readiness remains Atlas `review_required`, Beacon `supported`, Orbit `supported`.

Proof: `artifacts/multi-project-verification.json`, `pytest-multi-project.xml`, `browser-multi-project.json`, `browser-multi-display.json`, `live-multi-project.json`, `multi-project-preserved.json`, and `multi-*-desktop/mobile.png`.

## Reproduce and limits

Run the full suite with the project Python: `python -m pytest -q --basetemp=.runtime\pytest-all-multi --junitxml=artifacts/pytest-multi-project.xml`. Build with `npm.cmd --prefix frontend run build`.

Browser verification uses `scripts/browser-multi-project.cjs`, the owned isolated `scripts/serve-lifecycle-qa.py` server on 8000, installed Playwright and Chrome. It checks a QA marker and expects an initially unchanged fixture. Run `scripts/verify-live-projects.py` afterward against the same graph. Clean up and restore the normal backend using [RESTORATION.md](RESTORATION.md)'s instructions.

Repeated-cycle controls and a historical-event picker were subsequently implemented and verified in the [103-test cycle checkpoint](CYCLES.md). This document retains the original 90-test checkpoint. General source onboarding, arbitrary document extraction, authenticated reviewers, public company isolation, larger-load evaluation, full Docker execution and another-machine setup remain future work. This is a local synthetic company demo.
