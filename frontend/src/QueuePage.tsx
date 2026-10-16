import { useState } from "react";
import {
  ArrowRight,
  Check,
  CheckCheck,
  Clock3,
  FileText,
  ListChecks,
  ShieldCheck,
  Sparkles,
  TriangleAlert,
  X,
} from "lucide-react";
import { Badge, Button, EmptyState, initials, type RecordData } from "./ui";

export function QueuePage({
  overview,
  plan,
  selected,
  setSelected,
  onReview,
  onPropose,
  onApprove,
  onInspect,
  onInvestigate,
  onTransition,
  busy,
}: {
  overview: RecordData;
  plan: RecordData | null;
  selected: string[];
  setSelected: (ids: string[]) => void;
  onReview: (plan: RecordData) => void;
  onPropose: () => void;
  onApprove: () => void;
  onInspect: (id: string) => void;
  onInvestigate: () => void;
  onTransition: (item: RecordData, state: "completed" | "rejected") => void;
  busy: string;
}) {
  const [filter, setFilter] = useState("all");
  const changed = overview.history.length > 0;
  const resolved = changed && overview.history[0].event.state === "resolved";
  const stale = plan && plan.revision !== overview.revision;
  const open = overview.actions.filter(
    (item: RecordData) => item.action.state === "approved",
  ).length;
  const complete = overview.actions.filter(
    (item: RecordData) => item.action.state === "completed",
  ).length;
  const actions = overview.actions.filter(
    (item: RecordData) => filter === "all" || item.action.state === filter,
  );
  const proposals =
    plan?.proposals.filter((item: RecordData) => item.state === "proposed") ||
    [];
  return (
    <>
      <div className="queue-summary">
        <div>
          <Clock3 size={18} />
          <strong>{open}</strong>
          <span>Open follow-ups</span>
        </div>
        <div>
          <CheckCheck size={18} />
          <strong>{complete}</strong>
          <span>Completed</span>
        </div>
        <div>
          <ShieldCheck size={18} />
          <span>Every action starts with your approval.</span>
        </div>
      </div>
      <div className="queue-intro">
        <span className="small-icon">
          <ListChecks size={20} />
        </span>
        <p>
          Approval creates internal tasks. Communication stays a draft.
          Completing work alone does not restore approval.
        </p>
        {changed && !resolved && !plan && (
          <Button disabled={!!busy} onClick={onPropose}>
            Generate fresh plan <Sparkles size={15} />
          </Button>
        )}
      </div>
      {plan && (
        <section
          className="panel proposal-panel"
          aria-labelledby="proposal-title"
        >
          <div className="panel-heading">
            <div>
              <span className="section-label">PROPOSED RESPONSE / REVIEW</span>
              <h2 id="proposal-title">Review before creating work.</h2>
              <p>
                Select the follow-ups to create. Unselected proposals stay in
                history.
              </p>
            </div>
            <Badge tone="amber">
              {stale ? "Refresh required" : "Awaiting your approval"}
            </Badge>
          </div>
          {stale && (
            <div className="stale-plan" role="alert">
              <TriangleAlert size={19} />
              <p>
                The graph changed after this plan was prepared. Generate a fresh
                plan to review current evidence.
              </p>
              <Button variant="secondary" disabled={!!busy} onClick={onPropose}>
                Refresh plan
              </Button>
            </div>
          )}
          <div className="proposal-toolbar">
            <span>
              {selected.length} of {proposals.length} selected
            </span>
            <Button
              variant="text"
              disabled={!!busy || !!stale || !proposals.length}
              onClick={() =>
                setSelected(
                  selected.length === proposals.length
                    ? []
                    : proposals.map((item: RecordData) => item.id),
                )
              }
            >
              {selected.length === proposals.length
                ? "Deselect all"
                : "Select all"}
            </Button>
          </div>
          {proposals.length ? (
            <div className="proposals">
              {proposals.map((item: RecordData) => (
                <label
                  key={item.id}
                  className={`proposal ${selected.includes(item.id) ? "is-selected" : ""}`}
                >
                  <input
                    type="checkbox"
                    checked={selected.includes(item.id)}
                    disabled={!!busy || !!stale}
                    onChange={(e) =>
                      setSelected(
                        e.target.checked
                          ? [...selected, item.id]
                          : selected.filter((id) => id !== item.id),
                      )
                    }
                  />
                  <span>
                    <strong>{item.name}</strong>
                    <small>{item.reason}</small>
                  </span>
                  <Badge>Proposed</Badge>
                </label>
              ))}
            </div>
          ) : (
            <EmptyState
              icon={<CheckCheck size={26} />}
              title="The recorded work is already covered."
            >
              There are no new proposals in this plan. Review the persisted
              follow-ups below.
            </EmptyState>
          )}
          {plan.missing_owners?.length > 0 && (
            <p className="message error" role="alert">
              {plan.missing_owners.length} affected items have no resolved owner
              and require manual review.
            </p>
          )}
          <div className="draft">
            <div>
              <FileText size={16} />
              <span className="section-label">
                INTERNAL COMMUNICATION · DRAFT ONLY
              </span>
              <Badge>Not sent</Badge>
            </div>
            <p>{plan.draft}</p>
          </div>
          <div className="panel-footer approval-footer">
            <span>
              Evidence revision {plan.revision} · Human approval required
            </span>
            <Button
              disabled={!selected.length || !!busy || !!stale}
              onClick={onApprove}
            >
              <Check size={16} />
              Approve selected tasks
            </Button>
          </div>
        </section>
      )}
      <section className="panel actions-panel" aria-labelledby="actions-title">
        <div className="panel-heading">
          <div>
            <span className="section-label">PERSISTED WORK</span>
            <h2 id="actions-title">Follow-ups with a trail.</h2>
          </div>
          <span className="count-label">{overview.actions.length} total</span>
        </div>
        {overview.actions.length > 0 && (
          <div className="filter-tabs" aria-label="Filter follow-ups">
            {[
              ["all", "All work"],
              ["approved", "Open"],
              ["completed", "Completed"],
              ["rejected", "Rejected"],
            ].map(([value, title]) => (
              <button
                key={value}
                aria-pressed={filter === value}
                className={filter === value ? "active" : ""}
                onClick={() => setFilter(value)}
              >
                {title}
                <span>
                  {value === "all"
                    ? overview.actions.length
                    : overview.actions.filter(
                        (item: RecordData) => item.action.state === value,
                      ).length}
                </span>
              </button>
            ))}
          </div>
        )}
        {actions.length ? (
          <div className="actions">
            {actions.map((item: RecordData) => (
              <div className="action" key={item.action.id}>
                <span className="person-avatar">
                  {initials(item.owner || "?")}
                </span>
                <div className="action-text">
                  <button onClick={() => onInspect(item.action.id)}>
                    {item.action.name}
                  </button>
                  <small>
                    {item.owner} · {item.trigger}
                  </small>
                  <span>
                    Decision, change event, evidence, and owner linked
                  </span>
                </div>
                <Badge
                  tone={
                    item.action.state === "approved"
                      ? "amber"
                      : item.action.state === "rejected"
                        ? "neutral"
                        : "mint"
                  }
                >
                  {item.action.state === "approved"
                    ? "Open"
                    : item.action.state}
                </Badge>
                {item.action.state === "approved" && (
                  <div className="action-controls">
                    <Button
                      variant="secondary"
                      disabled={!!busy}
                      onClick={() => onTransition(item, "completed")}
                    >
                      <Check size={14} /> Complete
                    </Button>
                    <button
                      className="icon-button reject-button"
                      aria-label={`Reject ${item.action.name}`}
                      title="Reject follow-up"
                      disabled={!!busy}
                      onClick={() => onTransition(item, "rejected")}
                    >
                      <X size={17} />
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <EmptyState
            icon={<ListChecks size={27} />}
            title={
              overview.actions.length
                ? "No follow-ups in this view."
                : "A clear queue. An intentional next step."
            }
            action={
              overview.actions.length ? (
                <Button variant="text" onClick={() => setFilter("all")}>
                  View all work
                </Button>
              ) : (
                <Button variant="secondary" onClick={onInvestigate}>
                  Open change investigation <ArrowRight size={15} />
                </Button>
              )
            }
          >
            {overview.actions.length
              ? "Choose another filter to see your recorded work."
              : changed
                ? "Generate a response plan, review the evidence, and approve the relevant work."
                : "Record a synthetic prerequisite change to investigate its consequences before creating work."}
          </EmptyState>
        )}
      </section>
      {overview.plans.length > 0 && (
        <details className="panel plan-history">
          <summary>
            Proposal history <span>{overview.plans.length} recorded plans</span>
          </summary>
          <div>
            {overview.plans.map((item: RecordData) => (
              <div className="history-plan" key={item.plan.id}>
                <div>
                  <strong>Response plan · revision {item.plan.revision}</strong>
                  <small>
                    {item.proposals.length} proposals ·{" "}
                    {item.plan.revision === overview.revision
                      ? "Current revision"
                      : "Historical revision"}
                  </small>
                </div>
                <Button
                  variant="secondary"
                  onClick={() =>
                    onReview({ ...item.plan, proposals: item.proposals })
                  }
                >
                  Review this plan <ArrowRight size={14} />
                </Button>
              </div>
            ))}
          </div>
        </details>
      )}
    </>
  );
}
