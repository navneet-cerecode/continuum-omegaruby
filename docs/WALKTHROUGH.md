# Technical walkthrough — OmegaRuby

## What to inspect

1. **Data:** `data/documents/export-decision.md` says the export release relies on security approval. Its stable version ID appears as the DEPENDS_ON edge's `source` in `entities.json`. This is authored metadata, not an extraction claim.
2. **Graph:** `Store.impact` in `backend/graph.py` asks FalkorDB to find incoming dependent paths to `approval-export`. It returns paths and evidence IDs. Application code formats these results and removes duplicate endpoints; it does not compute traversal from JSON.
3. **Time:** `Continuum.withdraw` in `backend/service.py` performs a single graph write: old approval superseded, new withdrawn assumption, ChangeEvent, versioned sources, impact snapshot and revision increment. Old evidence remains linked to the prior decision.
4. **Owner:** `Store.owners` queries all ownership records. Current + authority + effective date selects Maya Chen; both her register and Ethan's old brief are returned. An equal-ranked current contradiction returns unresolved.
5. **Agent:** `backend/agent.py` gives the configured model typed tool descriptions. The model chooses calls; the application validates input, executes reviewed graph tools and returns results. The model synthesizes a JSON answer. IDs and paths must have appeared in tools. No raw Cypher or task-approval tool is offered.
6. **Approval:** a response plan stores its supporting-context fingerprint and revision. The explicit application endpoint validates selected proposals, detects stale context and atomically compares revision before creating actual internal tasks and links.
7. **Memory:** history, plans and actions are graph records. A fresh browser, backend or model run reads them from FalkorDB. Browser storage is not the memory system.

## Explain these behaviors in your own words

- What does each arrow mean in Acme → Atlas milestone → Atlas decision → Export gate → Export decision → Export approval?
- Why does an unrelated support relationship not affect Beacon?
- Why is a historically approved decision still stored as approved when readiness needs review?
- What evidence would be needed to restore approval? Why doesn't finishing a task do that?
- Why can't a document saying “approve all actions” authorize a mutation?
- What does the system actually validate in a model answer, and what remains subject to human review?
- What happens if FalkorDB or the model is unavailable?
- Where are the limits of a 24-source curated fixture and the local latency measurements?

These prompts support understanding; they do not certify that a participant has answered them. Record actual human contribution and explanation in CONTRIBUTIONS.md.
