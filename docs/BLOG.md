# CONTINUUM: Building a Company Brain That Knows When Decisions Need Review

A launch is approved. The decision is documented. The customer has been promised a date.

Then a security prerequisite changes.

The original approval still exists, but its supporting assumptions no longer hold. Which decisions need review? Which milestones and customer commitments depend on them? Who owns the response now, and what evidence explains the answer?

That is the problem behind **CONTINUUM**, Team **OmegaRuby**'s project for **Graph Hacks by WeMakeDevs and FalkorDB**, entering **Track 3 — Company Brain**.

CONTINUUM connects decisions, versioned evidence, prerequisites, owners, and commitments in FalkorDB. It traces the consequences of a recorded change and prepares follow-ups for explicit review. Its central distinction is simple: **a historical decision can remain explainable while its current readiness requires review.**

- [Public source and local setup](https://github.com/navneet-cerecode/continuum-omegaruby)
- [Live application](https://continuum-omegaruby-production.up.railway.app/) — account access required; judge credentials are provided separately.
- [Recorded browser walkthrough](https://github.com/navneet-cerecode/continuum-omegaruby/releases/tag/v0.2.0)

![CONTINUUM company context interface](https://raw.githubusercontent.com/navneet-cerecode/continuum-omegaruby/main/artifacts/design/context-1440.png)

## The gap between finding a document and understanding a consequence

Searching for a launch document answers, “Where was the decision recorded?” CONTINUUM asks a different question: “What depended on that decision's prerequisites, and what changes when one of them is withdrawn?”

The demonstration uses **Northstar Systems**, a fictional company with Atlas, Beacon, and Orbit projects. Its Markdown sources and typed relationships are curated synthetic data. They are not real customer records or relationships automatically extracted from arbitrary prose.

In the Atlas scenario, an export approval supports an export decision, which supports a gate, which supports the Atlas launch decision and downstream commitments. Withdrawing the approval flags **seven affected records in this fixture**. That number is a known scenario result, not a general performance claim.

The application preserves the old approval and the evidence that justified the original decision. It changes the current readiness assessment to `review_required`; it does not declare the decision wrong or automatically cancel the launch.

## Modeling operational meaning in FalkorDB

The graph includes `Decision`, `Assumption`, `Project`, `Milestone`, `Commitment`, `Person`, and immutable `DocumentVersion` nodes. It also stores operational records: `ChangeEvent`, `ResponsePlan`, `ProposedAction`, `ActionItem`, and `RestorationReview`.

The most important modeling choice is relationship meaning:

| Relationship | Meaning |
| --- | --- |
| `DEPENDS_ON` | A dependent points to its prerequisite; this relationship propagates impact. |
| `SUPPORTED_BY` | A record points to a particular source version. |
| `OWNED_BY` | A sourced ownership record points to a person. |
| `SUPERSEDES` | A newer state or source version retains a link to the older one. |
| `AFFECTS` | A change records the affected-item membership observed for that event. |

An example dependency chain is:

```text
Customer commitment
  → Atlas availability
  → Atlas decision
  → Export gate
  → Export decision
  → Export approval

Every arrow means DEPENDS_ON.
```

Impact investigation starts at the changed prerequisite and finds incoming dependency paths. Ownership, team membership, and document links do not spread impact. Otherwise, sharing a team or a source could incorrectly make an unrelated project appear affected.

This is the core current-impact query from the project's [query reference](https://github.com/navneet-cerecode/continuum-omegaruby/blob/main/docs/QUERIES.cypher):

```cypher
MATCH p=(n)-[:DEPENDS_ON*1..8]->(a {id:$id})
WHERE (n:Decision OR n:Milestone OR n:Commitment OR n:Project)
  AND all(r IN relationships(p) WHERE coalesce(r.current,true)=true)
RETURN n.id AS id, n.name AS name, labels(n) AS labels,
       [v IN nodes(p) | v.id] AS path,
       [e IN relationships(p) | properties(e)] AS edges,
       length(p) AS depth
ORDER BY depth, id LIMIT 201;
```

The eight-hop bound is deliberate. The application retains up to 200 paths, uses the 201st as a truncation signal, and separately checks for active dependencies beyond the depth boundary. Incomplete investigation blocks response-plan generation. A bounded result should not quietly become a claim that every consequence was found.

FalkorDB also executes evidence retrieval, owner queries, history, and persisted follow-up operations. Organizational state stays in the graph, including proposals and approvals; private account configuration stores identity and access settings separately. The [graph model](https://github.com/navneet-cerecode/continuum-omegaruby/blob/main/docs/GRAPH_MODEL.md) documents these semantics.

## Current ownership needs evidence too

The Atlas fixture deliberately includes an older project brief naming Ethan Park and a current authoritative register naming Maya Chen.

CONTINUUM returns both sources and their conflict. Its owner resolution compares valid, sourced records using configured authority and effective dates. Equal-ranked records must agree; unresolved ownership does not become a guessed assignment.

This matters because a plausible response sent to an outdated owner is still a broken workflow. Stable person IDs also prevent similarly named people from being silently merged.

## From a change to a reviewable response

The complete workflow is:

1. Inspect the project's readiness, dependency paths, and source versions.
2. Record a clearly labeled synthetic prerequisite withdrawal.
3. Inspect affected records and their resolved owners or conflicts.
4. Generate a response plan and select proposed follow-ups.
5. Explicitly approve the selection to create persisted action items.
6. Record replacement evidence and complete a separate restoration review.

A proposal captures the graph revision and a fingerprint of its supporting context. Approval rechecks those values, and task creation uses an atomic graph revision comparison. Changed evidence, dependencies, or ownership makes the old proposal stale. Repeating approval does not create duplicate tasks.

Completing a follow-up does **not** restore the security approval. Restoration requires replacement evidence and explicit revalidation of the affected records. Earlier sources, tasks, and incidents remain available for explanation, including across repeated change cycles.

The application prepares communication drafts but sends no external messages.

## Giving the model useful tools and clear limits

The model selects among eight typed, read-only graph tools. It can retrieve evidence, trace impact, resolve ownership, and assess readiness. It cannot execute unrestricted Cypher, approve plans, change graph records, or send notifications.

Returned answers are checked against retrieved source IDs and complete graph paths. Invalid tool arguments, invented citations, and fabricated paths are rejected. These checks establish structural grounding; they do **not** prove that every natural-language sentence is entailed by the evidence. That remains an evaluation gap and a reason to inspect the cited sources.

Local inference is supported through Ollama. The deployed application was verified using Groq Free with `openai/gpt-oss-120b`.

One concrete deployment lesson came from the provider protocol. The initial combination of JSON response mode and tool calling was rejected. Removing JSON mode exposed another failure: the model sometimes attempted to call a nonexistent `json` tool to finish its answer.

The integration now provides a `finish_investigation` function carrying the answer schema. It returns a validated answer without mutating records. The same source, path, retrieval-first, and revision checks still apply. This made the final-answer contract explicit rather than relying on a prompt to repair an API mismatch. The implementation is in [backend/agent.py](https://github.com/navneet-cerecode/continuum-omegaruby/blob/main/backend/agent.py).

## Deploying and checking the actual workflow

The stack is React and TypeScript, FastAPI, and FalkorDB. A Docker application serves the built frontend and API from one HTTPS origin on Railway. FalkorDB runs privately with a persistent volume and append-only persistence enabled.

The current application uses one worker and one replica because sessions and some limits are process-local. Horizontal scaling would require additional shared infrastructure.

The [cloud verification report](https://github.com/navneet-cerecode/continuum-omegaruby/blob/main/artifacts/cloud-verification.json) records executed checks:

- **129 automated tests passed**, along with container lifecycle checks in GitHub Actions.
- Authentication, origin restrictions, CSRF handling, role restrictions, and authenticated graph reads passed the recorded checks.
- A cloud rehearsal traced seven impacted Atlas records, approved and completed one follow-up, and restored readiness through separate replacement-evidence review.
- A real FalkorDB restart retained the complete recap: its SHA-256 hash matched before and after the restart.
- A live Beacon model investigation returned the expected dependency path and all four required source versions.

These are checks on this implementation and its synthetic scenarios. They do not establish enterprise scale, a comprehensive security audit, or semantic correctness for arbitrary model answers.

## What this project taught us

The useful unit of organizational memory is often a **decision connected to its prerequisites and evidence**. Keeping those connections explicit makes it possible to explain both the original rationale and the need for a later review.

Three design lessons stand out:

- Relationship direction and meaning are product behavior. A graph can be connected without every connection implying operational impact.
- Time and authority belong in the data model. “The newest text mentions someone” is too weak a rule for current ownership or approval.
- Proposals, approved tasks, and restored readiness need separate states. Collapsing them would let administrative progress masquerade as renewed evidence.

The next improvements would be permission-aware connectors for real sources, stronger evaluation of answer entailment, and shared sessions and quotas for multiple application replicas. Those are future work. Current onboarding accepts reviewed synthetic Markdown with curated metadata.

The live deployment uses Railway trial resources and Groq Free inference. Availability depends on remaining trial credits, service limits, and model access; complete local setup is included in the repository.

**CONTINUUM's goal is to make a changed assumption visible, explain its consequences, and give the right people a reviewable next step.**

Explore the [source, setup, and graph model](https://github.com/navneet-cerecode/continuum-omegaruby), open the [live application](https://continuum-omegaruby-production.up.railway.app/), or watch the [release walkthrough](https://github.com/navneet-cerecode/continuum-omegaruby/releases/tag/v0.2.0).
