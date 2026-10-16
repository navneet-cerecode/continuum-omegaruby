import { useRef, useState } from "react";
import {
  Activity,
  ArrowRight,
  BookOpen,
  Check,
  CircleDot,
  Clock3,
  FileSearch,
  GitBranch,
  Layers3,
  Search,
  ShieldCheck,
  TriangleAlert,
  Users,
} from "lucide-react";
import {
  api,
  Badge,
  Button,
  EmptyState,
  initials,
  type RecordData,
  type View,
} from "./ui";
import { AskPanel, type Work } from "./AskPanel";

export function ContextPage({
  overview,
  ready,
  impact,
  configured,
  busy,
  work,
  onInspect,
  onNavigate,
  onWithdraw,
}: {
  overview: RecordData;
  ready: RecordData;
  impact: RecordData | null;
  configured: boolean;
  busy: string;
  work: Work;
  onInspect: (id: string) => void;
  onNavigate: (view: View) => void;
  onWithdraw: () => void;
}) {
  const changed = overview.history.length > 0;
  const resolved = changed && overview.history[0].event.state === "resolved";
  const flagged = ready.status === "review_required";
  const uncertain = ready.status === "unknown";
  const counts = Object.fromEntries(
    overview.counts.map((item: RecordData) => [item.kind, item.count]),
  );
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<RecordData[] | null>(null);
  const [searched, setSearched] = useState("");
  const searchSequence = useRef(0);
  const owner = ready.owner_resolution.owner?.name || "Needs resolution";
  const project = ready.project;
  const date = project.launch_date
    ? new Date(project.launch_date + "T12:00:00").toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
      })
    : "Date unrecorded";
  return (
    <>
      <div className="stats" aria-label="Workspace totals">
        {[
          [
            "Company projects",
            counts.Project || 0,
            Layers3,
            "Connected initiatives",
          ],
          [
            "Knowledge sources",
            counts.Document || 0,
            BookOpen,
            "Versioned evidence",
          ],
          [
            "Recorded decisions",
            counts.Decision || 0,
            GitBranch,
            "With their original rationale",
          ],
          [
            "Current review flags",
            flagged ? 1 : 0,
            Activity,
            flagged
              ? "A prerequisite needs attention"
              : uncertain
                ? "Readiness evidence incomplete"
                : "Current prerequisites supported",
          ],
        ].map(([label, value, Icon, detail]: any) => (
          <div
            className={`stat ${label === "Current review flags" && flagged ? "warning" : ""}`}
            key={label}
          >
            <span>
              <Icon size={16} />
              {label}
            </span>
            <div>
              <strong>{String(value).padStart(2, "0")}</strong>
              <small>{detail}</small>
            </div>
          </div>
        ))}
      </div>
      <div className="context-grid">
        <section className="panel launch-panel" aria-labelledby="launch-title">
          <div className="panel-heading">
            <span className="section-label">IN FOCUS / LAUNCH READINESS</span>
            <span className="launch-date">
              <Clock3 size={14} />
              {date}
            </span>
          </div>
          <div className="launch-title">
            <span className="project-icon">
              <Layers3 size={25} />
            </span>
            <div>
              <h2 id="launch-title">{project.name}</h2>
              <p>{project.description}</p>
            </div>
            <Badge
              tone={
                flagged
                  ? "amber"
                  : ready.status === "supported"
                    ? "mint"
                    : "neutral"
              }
            >
              {flagged
                ? "Review required"
                : ready.status === "supported"
                  ? "Supported"
                  : "Unknown"}
            </Badge>
          </div>
          <div
            className={`readiness-summary ${flagged || uncertain ? "needs-review" : ""}`}
          >
            {flagged || uncertain ? (
              <TriangleAlert size={20} />
            ) : (
              <ShieldCheck size={20} />
            )}
            <p>{ready.conclusion}</p>
          </div>
          {ready.issues?.length > 0 && (
            <details className="readiness-gaps">
              <summary>
                {ready.issues.length} readiness evidence{" "}
                {ready.issues.length === 1 ? "gap" : "gaps"} to inspect
              </summary>
              <ul>
                {ready.issues.map((item: RecordData, i: number) => (
                  <li key={i}>{item.message}</li>
                ))}
              </ul>
              <p>
                Assessment{" "}
                {ready.complete
                  ? "within recorded traversal bounds"
                  : "incomplete"}{" "}
                · maximum {ready.max_hops} hops · {ready.path_limit} paths.
              </p>
            </details>
          )}
          <div className="readiness-checks">
            {(overview.prerequisites || []).map((item: RecordData) => {
              const check = ready.checks?.find(
                (entry: RecordData) => entry.id === item.id,
              );
              const withdrawal = overview.project_history?.find(
                (entry: RecordData) =>
                  entry.previous.id === item.id &&
                  entry.event.state === "unresolved",
              )?.event;
              return (
                <button
                  key={item.id}
                  onClick={() =>
                    onInspect(
                      withdrawal
                        ? withdrawal.withdrawn_assumption_id ||
                            item.id + "-withdrawn"
                        : item.id,
                    )
                  }
                >
                  <ShieldCheck size={18} />
                  <span>{item.name}</span>
                  <Badge
                    tone={check?.assessment === "supported" ? "mint" : "amber"}
                  >
                    {withdrawal
                      ? "Withdrawn"
                      : check?.assessment === "supported"
                        ? item.state === "confirmed"
                          ? "Confirmed"
                          : "Approved"
                        : "Evidence gap"}
                  </Badge>
                  <ArrowRight size={14} />
                </button>
              );
            })}
            <button onClick={() => onInspect(project.id)}>
              <Users size={18} />
              <span>Current launch owner</span>
              <span className="owner-inline">
                <span className="person-avatar mini">{initials(owner)}</span>
                <strong>{owner}</strong>
              </span>
              <ArrowRight size={14} />
            </button>
          </div>
          <div className="panel-footer">
            <Button
              variant="text"
              onClick={() => onInspect(project.decision_id || project.id)}
            >
              Inspect decision evidence <ArrowRight size={15} />
            </Button>
            <span>
              <GitBranch size={13} />
              Recorded graph paths
            </span>
          </div>
        </section>
        <section
          className={`radar-panel ${changed ? "has-change" : ""}`}
          aria-labelledby="radar-title"
        >
          <div className="radar-heading">
            <span className="section-label">ON YOUR RADAR</span>
            <CircleDot size={17} />
          </div>
          <div className="ripple-visual" aria-hidden="true">
            <div className="ripple-line" />
            <span className="ripple-node first">
              <ShieldCheck size={19} />
            </span>
            <span className="ripple-node second">
              <GitBranch size={19} />
            </span>
            <span className="ripple-node third">
              <Users size={19} />
            </span>
          </div>
          <h2 id="radar-title">
            {resolved
              ? "Replacement evidence.\nA recorded resolution."
              : changed
                ? "One changed approval.\nA connected impact."
                : "When a fact changes,\nthe context follows."}
          </h2>
          <p>
            {resolved
              ? "The selected incident was resolved through explicit review. Current readiness is assessed separately; inspect the retained incident history."
              : changed
                ? "A recorded prerequisite was withdrawn. Trace the decisions and promises that depend on it."
                : "Introduce a synthetic prerequisite update to trace recorded dependencies for this project."}
          </p>
          {changed && impact && (
            <div className="radar-metrics">
              <div>
                <strong>{String(impact.count).padStart(2, "0")}</strong>
                <span>connected items</span>
              </div>
              <div>
                <strong>
                  {String(
                    impact.items.filter(
                      (item: RecordData) => item.kind === "Commitment",
                    ).length,
                  ).padStart(2, "0")}
                </strong>
                <span>customer promises</span>
              </div>
            </div>
          )}
          <Button
            className="radar-action"
            disabled={!!busy || !overview.context.prerequisite_id}
            onClick={changed ? () => onNavigate("investigation") : onWithdraw}
          >
            {resolved
              ? "Review resolution"
              : changed
                ? "Investigate the change"
                : project.id === "project-atlas" &&
                    overview.context.prerequisite_id === "approval-export"
                  ? "Introduce security update"
                  : "Introduce prerequisite update"}
            <ArrowRight size={16} />
          </Button>
          {changed && overview.context.can_withdraw && (
            <Button
              variant="secondary"
              className="radar-action"
              disabled={!!busy}
              onClick={onWithdraw}
            >
              Record another update <ArrowRight size={16} />
            </Button>
          )}
          <small>
            {changed
              ? "Original approval retained in history."
              : "Synthetic data · Changes this fictional workspace."}
          </small>
        </section>
      </div>
      <div className="workflow-strip" aria-label="How context becomes action">
        {(
          [
            ["context", "01", "Understand the context", "Evidence & decisions"],
            [
              "investigation",
              "02",
              "Follow the change",
              "Dependencies & owners",
            ],
            [
              "queue",
              "03",
              "Decide what happens next",
              "Human-approved follow-ups",
            ],
          ] as const
        ).map(([view, number, label, detail], index) => (
          <button key={view} onClick={() => onNavigate(view)}>
            <span className="step-number">{number}</span>
            <span>
              <strong>{label}</strong>
              <small>{detail}</small>
            </span>
            {index < 2 ? <ArrowRight size={15} /> : <Check size={15} />}
          </button>
        ))}
      </div>
      <AskPanel
        eventId={overview.context.requested_event_id || undefined}
        ready={ready}
        configured={configured}
        busy={busy}
        work={work}
        onInspect={onInspect}
      />
      <section className="knowledge-section" aria-labelledby="knowledge-title">
        <div className="knowledge-heading">
          <div>
            <span className="section-label">THE CONNECTED WORKSPACE</span>
            <h2 id="knowledge-title">Company context, within reach.</h2>
          </div>
          <form
            className="search"
            onSubmit={(e) => {
              e.preventDefault();
              if (!query.trim()) {
                setResults(null);
                return;
              }
              const sequence = ++searchSequence.current;
              const term = query.trim();
              void work("Searching company context", async () => {
                const data = await api("/search?q=" + encodeURIComponent(term));
                if (sequence === searchSequence.current) {
                  setResults(data);
                  setSearched(term);
                }
              });
            }}
          >
            <Search size={16} />
            <input
              aria-label="Search company context"
              placeholder="Search people, sources, projects…"
              maxLength={100}
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                searchSequence.current++;
                setResults(null);
              }}
            />
            <button
              type="submit"
              disabled={!!busy}
              aria-label="Search company graph"
            >
              <ArrowRight size={17} />
            </button>
          </form>
        </div>
        {results !== null ? (
          <div className="search-results panel">
            <div className="results-heading">
              <span role="status">
                {results.length} results for “{searched}”
              </span>
              <Button
                variant="text"
                onClick={() => {
                  setQuery("");
                  setResults(null);
                }}
              >
                Clear search
              </Button>
            </div>
            {results.length ? (
              results.map((result) => (
                <button
                  className="entity-result"
                  key={result.entity.id}
                  onClick={() => onInspect(result.entity.id)}
                >
                  <span className="source-icon">
                    <FileSearch size={18} />
                  </span>
                  <span>
                    <strong>{result.entity.name}</strong>
                    <small>
                      {result.labels[0]} · {result.entity.id}
                    </small>
                  </span>
                  <ArrowRight size={16} />
                </button>
              ))
            ) : (
              <EmptyState
                icon={<Search size={24} />}
                title="No matching context"
              >
                Try “Atlas”, “security”, or a person’s name.
              </EmptyState>
            )}
          </div>
        ) : (
          <div className="projects">
            {overview.projects.map((item: RecordData, index: number) => (
              <button
                className="project-row"
                key={item.project.id}
                onClick={() => onInspect(item.project.id)}
              >
                <span className={`project-tile tile-${index}`}>
                  <Layers3 size={21} />
                </span>
                <span className="project-row-text">
                  <strong>{item.project.name}</strong>
                  <small>{item.project.description}</small>
                </span>
                <Badge
                  tone={
                    item.project.id === project.id && flagged
                      ? "amber"
                      : "neutral"
                  }
                >
                  {item.project.id === project.id && flagged
                    ? "Review required"
                    : item.project.state}
                </Badge>
                <ArrowRight size={17} />
              </button>
            ))}
          </div>
        )}
      </section>
    </>
  );
}
