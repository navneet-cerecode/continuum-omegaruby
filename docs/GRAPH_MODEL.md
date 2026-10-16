# Graph model — CONTINUUM / OmegaRuby

The default graph represents fictional Northstar Systems. Optional account mode selects a distinct company graph from server-controlled account configuration; clients cannot choose a graph. Application-level separation is tested across two graphs, without an infrastructure-isolation claim. All organizational context, approvals, history, proposals and tasks live in FalkorDB; the private account configuration stores identity/access settings only. See [ACCESS.md](ACCESS.md).

Project/prerequisite selection scopes all three curated workflows. `data/extensions/multi-project.json` discloses Orbit gates and Beacon accountability. Events record project/prerequisite/source IDs; legacy Atlas events derive them from stored links. Shared prerequisites retain global impact and require every affected project's projected readiness before restoration. See [MULTI_PROJECT.md](MULTI_PROJECT.md).

## Entities

| Label | Role |
|---|---|
| Person | Stable identified person; never deduplicated using name similarity |
| Team | Organizational group |
| Project | Atlas, Beacon or Orbit |
| Milestone | Delivery/availability gate |
| Document | Stable source document identity |
| DocumentVersion | Immutable excerpt, source hash, version, authority, effective date, current flag |
| Decision | Recorded choice; changed assumptions do not erase or invalidate it |
| Assumption | A prerequisite, including security approval and capacity |
| Commitment | Explicit promise to a fictional customer |
| ChangeEvent | Applied update with time, synthetic marker, state, evidence and new-cycle lineage/snapshot metadata |
| ActionItem | Actual internal task created by application-controlled approval |
| Workspace | Revision used for atomic stale-state checks |
| ResponsePlan | Persisted proposal snapshot, supporting-context hash and communication draft |
| ProposedAction | Proposed work, separate from actual ActionItem records |
| RestorationReview | Pending/approved replacement evidence and explicit revalidation record |

Application IDs are stable strings. Import uses allowlisted labels/relationship types and parameterized values. Fixture entities and topology originate in `data/entities.json`; prose and subject provenance originate in the Markdown source manifest. This is curated metadata, not LLM extraction. `classification` records confirmed metadata claims; the data is still fictional. Source conflicts are returned explicitly. Missing data is unknown, never treated as a safe result. There are no claimed inferred relationships.

## Relationships: direction and meaning

| Relationship | Direction | Meaning / propagation |
|---|---|---|
| MEMBER_OF | Person → Team | Membership. Does not propagate impact. |
| OWNED_BY | Project/Decision/Milestone/Commitment → Person | Sourced authority, validity and current ownership. Does not propagate. |
| PART_OF | DocumentVersion → Document; Decision/Milestone → Project | Version grouping or containment. Does not propagate. |
| DEPENDS_ON | Dependent → Prerequisite | Explicit operational dependency. **Only this type propagates impact.** |
| SUPPORTED_BY | Entity/ActionItem → DocumentVersion | Direct versioned evidence. Does not propagate. |
| RECORDED_IN | Entity → DocumentVersion | Supported retrieval alias for a recorded claim. No fixture instances required. |
| SUPERSEDES | New Assumption/ChangeEvent → Old Assumption; New DocumentVersion → Old DocumentVersion | History; old state retained. Does not propagate. |
| AFFECTS | ChangeEvent → affected entity | Snapshot of affected items at the change. Does not further propagate. |
| ASSIGNED_TO | ActionItem → Person | Owner at approval. Historical assignments preserved. |
| TRIGGERED_BY | ActionItem/ResponsePlan → ChangeEvent | Causal audit trail. |
| FOR_DECISION | ActionItem → Decision or Commitment | Item whose response task was approved; name covers commitment review too. |
| HAS_PROPOSAL | ResponsePlan → ProposedAction | Reviewable work selection. |
| CREATED_FROM | ActionItem → ProposedAction | Exact approved proposal(s). |
| PROPOSES | RestorationReview → Assumption | Candidate replacement, before activation. |
| RESOLVES | RestorationReview → ChangeEvent | Explicit approved resolution. |
| REVALIDATES | RestorationReview → affected entity | Exact reviewed item set. |
| REVIEWED_BY | RestorationReview → Person | Synthetic launch-owner role recorded at review. |

## Impact semantics

Starting from `approval-export`, match incoming current `DEPENDS_ON` paths with 1–8 relationships. Eligible impacted endpoints: Decision, Milestone, Project, Commitment. Eight-hop bound, 200 retained path limit, query timeout and 7 expected impacted IDs in the fixture. Deduplicate endpoints and retain the shortest returned path. Fetch a 201st path as a limit sentinel and query for an active incoming edge beyond eight hops. Either makes impact incomplete and blocks response plans. Cycles cannot create unbounded traversal; a dense graph may still exhaust the bounded query budget and require a narrower investigation.

Example stored direction:

```text
Acme commitment → Atlas availability → Atlas decision → Export gate → Export decision → Export approval
                  depends on at every arrow
```

Impact travels in the opposite direction from the changed prerequisite. Team membership, containment, ownership and supporting documents never spread impact. Removing the Atlas decision → Export gate relationship removes its downstream chain from the impact query. Adding an unrelated source relationship does not add Beacon.

`AFFECTS` preserves affected-item membership. New ChangeEvents also store the full bounded impact JSON and its SHA-256 checksum, capturing withdrawal-time paths, edge evidence, sources and ownership. Resolved historical views validate and read that payload; unresolved investigations recompute current `DEPENDS_ON` paths. A later topology or ownership edit can therefore differ from the historical snapshot. Legacy events without the payload reconstruct retained paths and disclose that their metadata is not an event-time snapshot. A checksum is not an administrator-resistant signature.

New events record a root `lineage_id`, `cycle_index` and `previous_event_id`; replacement assumptions carry the root ID. Legacy roots are discovered through bounded supersession paths. Restoration changes the current prerequisite, while historical selection remains read-only. Event-specific evidence/review IDs and revision checks isolate repeated cycles. The picker exposes 100 recent project incidents, with explicit truncation and direct-ID access for older records. See [CYCLES.md](CYCLES.md).

## Time, authority, sources

Old export approval becomes `current=false`, `state=superseded`, `valid_to=change time`. New withdrawn assumption is `current=true`. Old dependencies still point to the original approval so the historical decision remains explainable. Readiness detects that its prerequisite is no longer current; it does not substitute the withdrawal as approving evidence. Decision status remains approved as a historical record, while readiness is review_required.

Readiness requires every `Project.required_assumptions` ID to be reachable. Each assumption's `required_evidence_authority` must match a current valid source with excerpt/hash/provenance. Readiness separately checks dependency sources, assumption validity and resolved ownership. Missing policy/evidence, an invalid source, or incomplete 50-path/eight-hop traversal prevents a supported result. Known withdrawals/disputes require review. This is curated policy enforcement, not prose entailment.

Ownership selects current, effective, sourced records by numeric authority, then parsed timezone-aware effective-date recency. The current ownership register has authority 100; the historical project brief has authority 20. Return both source excerpts and the conflict. All equal-ranked current owners must agree; incomplete or malformed records return no resolved owner. Plans omit those assignments and list missing owners. Import metadata can establish authority; the model cannot invent it.

DocumentVersion hashes reject in-place edits. Import a higher-numbered new version with a later effective date and `supersedes` pointing to the sole current version of the same document. Old source versions stay linked to their original decisions. Reimport returns a no-op and never restores a superseded approval. Metadata and all subjects validate before a single guarded document mutation; revision checks reject competing application changes before writes. Whole-fixture seeding remains a trusted multiwrite operation.

## Action consistency

Proposals snapshot graph revision and a hash of impacted paths, edge evidence, current owners and supporting versions. Approval checks membership, fingerprint and revision. The revision compare and task creation execute in one atomic Cypher query. Other application mutations advance the revision. Direct administrator edits are outside application control: their supporting-context changes are detected before approval, but racing an unmanaged database write against application approval is not a supported production consistency model.

Task states: approved → completed or rejected. Proposed work uses ProposedAction state proposed/approved. Completing a task never resolves the ChangeEvent or restores an assumption. The separate [restoration workflow](RESTORATION.md) records replacement evidence, checks prerequisites and closed follow-ups, and requires explicit revalidation. Approval retains old edges with `current=false`, creates sourced replacement edges, updates project policy and records resolution/reviewer/rationale. Reseeding does not reactivate historical edges.
