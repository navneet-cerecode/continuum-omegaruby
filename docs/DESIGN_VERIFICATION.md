# CONTINUUM redesign verification

Verified October 16, 2026 in installed Google Chrome on Windows. The frontend was built and the actual rendered product inspected before and after implementation. The final build is available through the existing FastAPI server at http://127.0.0.1:8000/#context.

## Delivered experience

- Forest navigation, warm neutral canvas, deliberate typography, semantic state colors, and reusable controls.
- Three distinct compositions for readiness, dependency investigation, and follow-up review.
- URL navigation with browser history, page titles, heading focus, and a skip link.
- Ctrl/Cmd+K search with keyboard commands, abortable typeahead, and explicit result/error/empty states.
- Interactive dependency nodes and edge evidence, with a vertical mobile path and responsive native table.
- Source-version explorer with nested back navigation, focus containment, focus return, and fullscreen mobile layout.
- Explicit staged/recorded states, stale-plan approval blocking, proposal selection, task filters, and transition confirmation.
- Structural loading, inline failures, retry, success feedback, and reduced motion.

Backend routes, graph traversal, approval validation, persistence, model adapters, and source fixtures were preserved. No production dependencies were added. Axe was fetched only into ignored `.runtime/design-tools` for QA.

## Evidence

| Check                                | Result                                                                                                              |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------- |
| TypeScript and Vite production build | Passed                                                                                                              |
| Existing regression suite            | 32 passed; one dependency deprecation warning                                                                       |
| Isolated browser workflow            | 13 grouped checks passed, using real FastAPI and FalkorDB                                                           |
| Final production browser audit       | 8 read-only grouped checks passed                                                                                   |
| Responsive matrix                    | All three screens at 320, 375, 430, 768, 1024, 1440, and 1920 pixels; no horizontal document overflow               |
| Automated accessibility              | Axe-core 4.14.0; nine scans; zero violations in selected WCAG 2 A/AA, 2.1 A/AA, and 2.2 AA rules                    |
| Keyboard                             | Search, graph nodes/edges, nested evidence, dialog focus containment, Escape, focus return, task selection          |
| Reduced motion                       | Dialog animation computed as `none`                                                                                 |
| Real application responses           | No unexpected API failures or browser exceptions in the final browser audits                                        |
| Live model                           | Configured local agent returned a grounded review-required conclusion, five source links, and visible tool activity |
| Original workspace                   | Revision 26 and original actions retained; live agent verification confirms no organizational mutation              |

The automated accessibility scans cover context, investigation, and queue at 375 and 1440 pixels; the desktop evidence drawer; mobile search; and mobile evidence. Earlier findings in contrast, visible/accessibility label alignment, and dialog focus wrapping were corrected before these passing scans.

## Complete workflow verified

The mutation run used a separately seeded graph with model inference disabled, and a task-local Vite proxy at port 5173 to its API at port 8001. It did not mutate the original workspace.

1. Inspect readiness, search real sources, and navigate nested evidence using the keyboard.
2. Record the synthetic security withdrawal and verify exactly seven impacted items, excluding Beacon and Orbit.
3. Open connection evidence, select another dependency path, and expand a complete impact explanation.
4. Generate four proposals, select two, and approve exactly two persisted tasks.
5. Cancel a completion, confirm a completion, cancel a rejection, and confirm a rejection.
6. Verify persisted action states and that completing work still leaves readiness under review.
7. Simulate a concurrent user's real graph approval, refresh the first session, and verify stale approval is blocked until regeneration.
8. Start a fresh browser session and recover the persisted change and three total actions.

Additional explicitly simulated transport checks verified a slow initial overview, database outage and recovery, nested evidence failure announced inside the dialog, cancellation of an in-flight evidence request without reopening its drawer, and model failure with a released question form. These checks are UI-state evidence, not claims of real dependency outages.

## Visual QA and refinements

Baseline and final desktop/mobile screenshots were inspected. Refinements included stronger metadata contrast, larger primary text, desktop navigation that remains on one line, more usable mobile controls, native dialog behavior with explicit focus wrapping, and viewport screenshots for overlays. Mobile investigation uses a vertical path; mobile impact rows include visible field labels. Tables and dialogs were inspected for overflow and clipping.

| Artifact                          | Location                                                                                                   |
| --------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| Context                           | [Desktop](../artifacts/design/context-1440.png), [mobile](../artifacts/design/context-375.png)             |
| Investigation                     | [Desktop](../artifacts/design/investigation-1440.png), [mobile](../artifacts/design/investigation-375.png) |
| Queue                             | [Desktop](../artifacts/design/queue-1440.png), [mobile](../artifacts/design/queue-375.png)                 |
| Proposal selection                | [Review](../artifacts/design/proposal-review.png)                                                          |
| Stale proposal                    | [Recovery state](../artifacts/design/stale-plan.png)                                                       |
| Evidence                          | [Desktop](../artifacts/design/evidence-desktop.png), [mobile](../artifacts/design/evidence-mobile.png)     |
| Search                            | [Mobile dialog](../artifacts/design/search-mobile.png)                                                     |
| Live model                        | [Answer and evidence](../artifacts/design/live-agent.png)                                                  |
| Loading                           | [Structural skeleton](../artifacts/design/loading-state.png)                                               |
| Simulated outages                 | [Database](../artifacts/design/database-outage.png), [model](../artifacts/design/model-outage.png)         |
| Isolated test results             | [JSON](../artifacts/design/verification-isolated.json)                                                     |
| Production read-only results      | [JSON](../artifacts/design/verification-readonly.json)                                                     |
| Live model results                | [JSON](../artifacts/design/live-agent-verification.json)                                                   |
| Additional simulated state checks | [JSON](../artifacts/design/state-verification.json)                                                        |

## Bundle impact

| Production asset | Before   | After    | Change   |
| ---------------- | -------- | -------- | -------- |
| JavaScript, gzip | 78.66 kB | 83.41 kB | +4.75 kB |
| CSS, gzip        | 5.75 kB  | 10.79 kB | +5.04 kB |

One existing webfont family is retained with system fallbacks, preconnect hints, and `display=swap`. No raster imagery, animation framework, UI framework, scroll handlers, or heavyweight visualization dependency was added. Motion uses CSS transform/opacity and short control feedback. The original versions used two webfont families. Build sizes establish bundle cost; they are not a runtime performance benchmark.

## Reproduce checks

```powershell
npm.cmd --prefix frontend run build
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.runtime\pytest-design
```

The browser runner is `scripts/design-verify.cjs`. Set `PLAYWRIGHT_MODULE` to the installed Playwright module. Set `AXE_MODULE` to an installed `axe-core/axe.min.js` to include automated scans. It defaults to read-only checks against port 8000. Set `BASE_URL` to use another local server. Mutation checks require `DESIGN_MUTATION_QA=1` and refuse a graph with existing changes or actions; use a new, explicitly isolated graph and an allowed local frontend origin, as described above. Screenshots and machine-readable results are written under `artifacts/design`.

The existing `scripts/browser-verify.cjs` was updated for the redesigned heading. Its original requirement of a fresh demo graph still applies.

## Verification limits

Chrome desktop emulation was used; Firefox, Safari, physical mobile devices, and a full assistive-technology review were not performed. Passing automated rules does not establish complete WCAG conformance. The regression warning concerns Starlette's use of a deprecated AnyIO alias and does not indicate a failing test. Product/backend limitations documented in the project README still apply.
