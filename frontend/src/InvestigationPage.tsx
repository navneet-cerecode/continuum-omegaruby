import {
  Activity,
  ArrowDown,
  ArrowRight,
  Check,
  GitBranch,
  ShieldCheck,
  TriangleAlert,
} from "lucide-react";
import { FocusedGraph } from "./FocusedGraph";
import {
  Badge,
  Button,
  EmptyState,
  initials,
  PathView,
  Source,
  type RecordData,
} from "./ui";

export function InvestigationPage({
  overview,
  changed,
  impact,
  ready,
  busy,
  onInspect,
  onPropose,
  onWithdraw,
}: {
  overview: RecordData;
  changed: boolean;
  impact: RecordData | null;
  ready: RecordData;
  busy: string;
  onInspect: (id: string) => void;
  onPropose: () => void;
  onWithdraw: () => void;
}) {
  const resolved = overview.history[0]?.event.state === "resolved";
  const event = overview.history[0]?.event;
  const previous = overview.history[0]?.previous;
  return (
    <>
      <section
        className={`change-banner ${resolved ? "resolved" : changed ? "recorded" : "staged"}`}
      >
        <span className="alert-icon">
          {resolved ? (
            <ShieldCheck size={24} />
          ) : changed ? (
            <TriangleAlert size={24} />
          ) : (
            <Activity size={24} />
          )}
        </span>
        <div>
          <span className="section-label">
            {resolved
              ? "RECORDED CHANGE / RESOLVED"
              : changed
                ? "RECORDED CHANGE / UNRESOLVED"
                : "DEMO SCENARIO / NOT YET RECORDED"}
          </span>
          <h2>
            {resolved
              ? "Replacement approval reviewed and dependencies revalidated."
              : changed
                ? overview.context.prerequisite_name + " withdrawn."
                : "What if this prerequisite changes?"}
          </h2>
          <p>
            {resolved
              ? "The withdrawal and original rationale remain in history. Final launch sign-off remains a human decision."
              : changed
                ? "A prerequisite changed. Review the connected decisions and promises."
                : "Record the staged synthetic update to trace its impact. The original approval stays in history."}
          </p>
        </div>
        {!resolved && (
          <Button
            disabled={!!busy || (!changed && !overview.context.can_withdraw)}
            onClick={changed ? onPropose : onWithdraw}
          >
            {changed ? "Generate response plan" : "Record synthetic update"}
            <ArrowRight size={16} />
          </Button>
        )}
        {resolved && overview.context.can_withdraw && (
          <Button disabled={!!busy} onClick={onWithdraw}>
            Record another update <ArrowRight size={16} />
          </Button>
        )}
      </section>
      {overview.context.historical && (
        <p className="message" role="status">
          Historical incident ·{" "}
          {impact?.mode === "event_snapshot"
            ? "event-time snapshot"
            : "reconstructed retained history"}
          . Current project readiness: {ready.status}. Inspecting this incident
          does not change the active prerequisite.
        </p>
      )}
      {changed ? (
        <>
          <section
            className="panel impact-panel"
            aria-labelledby="impact-title"
          >
            <div className="panel-heading">
              <div>
                <span className="section-label">THE RIPPLE EFFECT</span>
                <h2 id="impact-title">
                  {impact?.count || 0} connected items{" "}
                  {resolved ? "revalidated" : "need review"}.
                </h2>
                <p>
                  Follow recorded dependencies to their evidence and accountable
                  owners.
                </p>
              </div>
              <Badge>
                {overview.projects
                  .filter(
                    (item: RecordData) =>
                      !impact?.items.some(
                        (affected: RecordData) =>
                          affected.id === item.project.id,
                      ),
                  )
                  .map((item: RecordData) =>
                    item.project.name.replace("Project ", ""),
                  )
                  .join(" & ")}{" "}
                excluded
              </Badge>
            </div>
            {impact?.truncated && (
              <p className="message error" role="alert">
                Result limit reached. This investigation is incomplete.
              </p>
            )}
            <FocusedGraph
              items={impact?.items || []}
              onInspect={onInspect}
              historical={overview.context.historical}
            />
            <div className="impact-table-wrap">
              <table className="impact-table">
                <caption className="sr-only">
                  Affected decisions and commitments, with current owner and
                  supporting evidence
                </caption>
                <thead>
                  <tr>
                    <th scope="col">Connected item</th>
                    <th scope="col">Type / depth</th>
                    <th scope="col">
                      {impact?.mode === "event_snapshot"
                        ? "Owner at withdrawal"
                        : "Current owner"}
                    </th>
                    <th scope="col">Evidence</th>
                  </tr>
                </thead>
                <tbody>
                  {impact?.items.map((item: RecordData) => (
                    <tr key={item.id}>
                      <td data-label="Connected item">
                        <button
                          className="item-link"
                          onClick={() => onInspect(item.id)}
                        >
                          {item.name}
                          <ArrowRight size={13} />
                        </button>
                      </td>
                      <td data-label="Type / depth">
                        <Badge>{item.kind}</Badge>
                        <small>{item.path.length - 1} hops</small>
                      </td>
                      <td
                        data-label={
                          impact?.mode === "event_snapshot"
                            ? "Owner at withdrawal"
                            : "Current owner"
                        }
                      >
                        <span className="table-owner">
                          {item.owner_resolution.owner?.name || "Unresolved"}
                        </span>
                      </td>
                      <td data-label="Evidence">
                        <details>
                          <summary>Why is this affected?</summary>
                          <div className="impact-evidence">
                            <PathView path={item.path} onInspect={onInspect} />
                            {item.path_evidence.map(
                              (source: RecordData, index: number) => (
                                <Source
                                  key={index}
                                  source={source}
                                  onInspect={onInspect}
                                />
                              ),
                            )}
                          </div>
                        </details>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="panel-footer">
              <span>
                <ShieldCheck size={15} />
                {resolved
                  ? "Dependencies revalidated; final launch sign-off remains with the launch lead."
                  : "Flagged for review. No decision invalidated and no launch cancelled."}
              </span>
              <span>Recorded dependencies · up to 8 hops</span>
            </div>
          </section>
          <div className="investigation-grid">
            <section className="panel history-panel">
              <div className="panel-heading">
                <div>
                  <span className="section-label">EVIDENCE HISTORY</span>
                  <h2>What changed</h2>
                </div>
                <GitBranch size={20} />
              </div>
              <div className="timeline">
                <div>
                  <span className="timeline-dot old" />
                  <Badge>SUPERSEDED · RETAINED</Badge>
                  <h3>{previous?.name}</h3>
                  <p>
                    The original source supported the recorded decision. It
                    remains available to explain the past decision.
                  </p>
                  <Button
                    variant="text"
                    onClick={() =>
                      onInspect(
                        previous?.id || overview.context.prerequisite_id,
                      )
                    }
                  >
                    Open original approval <ArrowRight size={14} />
                  </Button>
                </div>
                <ArrowDown size={18} />
                <div>
                  <span className="timeline-dot" />
                  <Badge tone="amber">
                    {resolved ? "WITHDRAWN · RETAINED" : "CURRENT · WITHDRAWN"}
                  </Badge>
                  <h3>Prerequisite update</h3>
                  <p>
                    This prerequisite was withdrawn pending a new authoritative
                    review.
                  </p>
                  <Source
                    source={{
                      id: overview.context.withdrawal_source_id,
                      name: "Synthetic prerequisite update",
                    }}
                    onInspect={onInspect}
                  />
                </div>
                {resolved && (
                  <>
                    <ArrowDown size={18} />
                    <div>
                      <span className="timeline-dot" />
                      <Badge tone="mint">REPLACEMENT · REVALIDATED</Badge>
                      <h3>Replacement approval reviewed</h3>
                      <p>
                        Replacement evidence was reviewed and the affected
                        dependencies were explicitly revalidated.
                      </p>
                      <Button
                        variant="text"
                        onClick={() => onInspect(event.restoration_review_id)}
                      >
                        Open revalidation record <ArrowRight size={14} />
                      </Button>
                    </div>
                  </>
                )}
              </div>
            </section>
            <section className="panel">
              <div className="panel-heading">
                <div>
                  <span className="section-label">CURRENT RESPONSIBILITY</span>
                  <h2>The owner behind the decision.</h2>
                </div>
                {ready.owner_resolution.conflict && (
                  <Badge tone="amber">Source conflict</Badge>
                )}
              </div>
              <div className="owner-resolution">
                <div className="owner-row">
                  <span className="person-avatar">
                    {initials(ready.owner_resolution.owner?.name || "?")}
                  </span>
                  <div>
                    <strong>
                      {ready.owner_resolution.owner?.name || "Unresolved"}
                    </strong>
                    <small>Current project owner</small>
                  </div>
                  <Check size={18} />
                </div>
                <p>
                  Current authority, effective dates and source validity
                  determine ownership. Conflicting records remain inspectable.
                </p>
                {ready.owner_resolution.sources.map((source: RecordData) => (
                  <Source
                    key={source.id}
                    source={source}
                    onInspect={onInspect}
                  />
                ))}
                <p className="policy">
                  Current records → authority → effective date. Equal-ranked
                  conflicts require human review.
                </p>
              </div>
            </section>
          </div>
          <p className="footnote">{impact?.caveat}</p>
        </>
      ) : (
        <section className="panel">
          <EmptyState
            icon={<GitBranch size={28} />}
            title="A change is where the investigation begins."
            action={
              <Button
                variant="text"
                onClick={() =>
                  onInspect(previous?.id || overview.context.prerequisite_id)
                }
              >
                Inspect the current approval <ArrowRight size={15} />
              </Button>
            }
          >
            The staged source is available, but its withdrawal has not been
            applied. Record the synthetic update above to explore the connected
            impact.
          </EmptyState>
        </section>
      )}
    </>
  );
}
