# CONTINUUM design audit and implementation plan

Audit completed on October 16, 2026 before frontend edits. Evidence: all frontend source, backend routes and graph/service contracts, architecture and runtime docs, baseline Chrome screenshots of all three views, real local API responses, and the existing verification scripts. The local workspace already contained one change event, two approved actions, and one historical plan; these records are retained.

## A. Current product assessment

CONTINUUM is a local, single-company demonstration built with React 19, TypeScript, Vite, plain CSS, and Lucide. FastAPI serves the production build and typed JSON endpoints; FalkorDB holds organizational context, dependencies, source versions, proposals, actions, and history. Optional model inference selects read-only graph tools. There is no public authentication or tenant system to redesign. Three client-side views cover company context, change investigation, and follow-up approval. The evidence drawer is shared across all flows.

The product's strongest feature is its explainable chain from changed evidence to dependencies, current owners, and human-approved tasks. The previous interface communicated this faithfully but felt small, pale, and uniform. A repeated panel treatment gave metrics, evidence, and actions similar visual weight.

## B. UX priorities

| Priority | Finding                                                                     | Response                                                                                                                    |
| -------- | --------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| Critical | Unapplied scenario headed as an already withdrawn approval                  | Explicit staged vs recorded language                                                                                        |
| Critical | Historical plan could present already approved proposals as selectable work | Only proposed items selectable; stale revision blocks approval and offers regeneration; backend checks remain authoritative |
| High     | No-result searches silently redisplayed the default project list            | Explicit result counts, no-match state, and clear-search action                                                             |
| High     | Recorded update left the primary next-step button disabled                  | Contextual action opens investigation                                                                                       |
| High     | Mobile squeezed full desktop navigation labels                              | Short, text-labeled navigation and full-width mobile evidence explorer                                                      |
| High     | Evidence text, form text, and annotations were very small and low contrast  | Stronger text colors, clearer type hierarchy, readable primary content                                                      |
| Medium   | Navigation had no URLs or browser history                                   | Hash navigation, back/forward, page titles, heading focus, skip link                                                        |
| Medium   | Dependency graph appeared after explanatory panels                          | Move actual dependency exploration before evidence history                                                                  |
| Medium   | Loading rendered a thin status banner and otherwise blank content           | Initial structural skeleton, status feedback, and retry state                                                               |
| Medium   | Task list mixed all task states                                             | Open/completed/rejected filters with counts and filter-specific empty states                                                |
| Medium   | Nested evidence inspection lost the previous entity                         | Evidence back trail                                                                                                         |
| Polish   | Mutations and busy feedback lacked consistent treatment                     | Shared controls, single in-flight mutation guard, explicit task transition confirmation                                     |

## C. Visual assessment

The old screen relied on numerous similarly rounded panels, tiny uppercase labels, faint green-gray copy, and generous space between largely equivalent sections. There were no major gradient or glass effects to remove. The redesign uses a dark forest navigation rail, warm paper canvas, open metric and project rows, and selective panels for readiness, investigation, and review. Amber signals an unresolved prerequisite; it does not imply an automatic launch cancellation.

## D. Research and capability inventory

- [Linear's UI redesign](https://linear.app/now/how-we-redesigned-the-linear-ui): strengthen hierarchy and alignment in navigation and application chrome; reduce repeated visual noise. No layout or assets copied.
- [Vercel Web Interface Guidelines](https://vercel.com/design/guidelines): keyboard operation, predictable focus, actionable feedback, form semantics, stable layout, responsive controls, and modest animation cost.
- [Emil Kowalski, Good vs Great Animations](https://emilkowal.ski/ui/good-vs-great-animations): origin-aware transitions, prompt feedback, restrained easing, and avoiding motion that interferes with functional data.
- [W3C modal dialog pattern](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/): native modal dialogs provide focus containment and inert background; Escape and focus return are verified.

Available relevant skills: Graphify, React best practices, verification, computer-use. Available design tools include 21st and Mobbin; no catalog assets are needed for this product. Graphify has no existing project graph or executable, so direct source and real runtime evidence establish the architecture. Impeccable, Emil-specific taste skills, UI UX Pro Max, frontend-design, interaction-design, animation, responsive, accessibility, and design-system skills were not present as named local skills. Equivalent public guidance was studied. No design library or animation dependency was installed.

## E. Design direction

Calm, technical, editorial, and accountable. Evidence should feel inspectable, risk should be easy to identify, and approval should feel deliberate. Forest green communicates navigation and actions; warm neutral surfaces support dense reading; amber communicates unresolved review. DM Sans is retained as the single webfont, with Segoe UI/system fallbacks. Headings use weight, scale, and tight tracking, rather than gradients. The team identity remains OmegaRuby, as defined in the current project.

## F. Design system

Semantic CSS variables cover background, foreground, surfaces, muted copy, border, accent, success, warning, destructive state, focus, radius, spacing, and motion. Shared primitives include Button, Badge, Source, PathView, EmptyState, CloseButton, and native Modal. Page-sized components own view-specific interaction; the application retains API state and mutations. Styles are split into foundation/context, workflow, overlays, and responsive rules. Lucide remains the sole icon family.

## G. Page plan

| Screen            | Composition and interaction                                                                                                                                                                     |
| ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Company context   | Open metric strip; readiness and clickable prerequisites; contextual radar action; three-step context loop; evidence-backed questions; project rows and explicit search results                 |
| Investigation     | Clearly staged or recorded banner; interactive dependency path first; complete native table, mobile record layout; retained source history; owner conflict and authority explanation            |
| Follow-up queue   | Open/completed summaries; proposed work separated from persisted actions; selection controls; stale-plan notice; communication draft; action filters; transition confirmation; proposal history |
| Evidence explorer | Entity identity, version/state, source excerpt, authority, ownership, relationships; nested back navigation; native focus containment; fullscreen mobile treatment                              |
| Workspace search  | Ctrl/Cmd+K, short navigation commands, debounced abortable graph search, arrow navigation, empty/error/loading states                                                                           |

## H. Motion

150ms control feedback; 200ms search/dialog appearance; 240ms evidence drawer motion from the right; compact loading indicators. Transform and opacity explain interaction without delaying it. No perpetual decorative animation, scroll listeners, animation library, or parallax. Reduced-motion disables animation and transitions.

## I. Implementation sequence

1. Preserve baseline screenshots and original frontend files in ignored runtime storage.
2. Establish shared semantic tokens, controls, native modal behavior, and error handling.
3. Refactor the shell and navigation without changing backend endpoints.
4. Recompose company context, evidence-backed questions, and search.
5. Move and rebuild dependency exploration with accessible native controls.
6. Refactor proposal review, persisted tasks, and stale-state feedback.
7. Apply mobile, tablet, laptop, desktop, and reduced-motion layouts.
8. Build and run the real application; inspect screenshots; refine visual issues.
9. Run existing regression tests and browser checks, including a complete mutation flow on an isolated FalkorDB graph.

Final evidence and limitations are documented in DESIGN_VERIFICATION.md.
