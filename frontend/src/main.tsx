import { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  ArrowRight,
  Check,
  ChevronRight,
  Database,
  GitBranch,
  Layers3,
  ListChecks,
  LoaderCircle,
  RefreshCw,
  Search,
  TriangleAlert,
  X,
} from "lucide-react";
import {
  api,
  Badge,
  Button,
  CloseButton,
  EmptyState,
  Modal,
  type RecordData,
  type View,
} from "./ui";
import { ContextPage } from "./ContextPage";
import { InvestigationPage } from "./InvestigationPage";
import { QueuePage } from "./QueuePage";
import { EvidenceDrawer } from "./EvidenceDrawer";
import { CommandSearch } from "./CommandSearch";
import { RestorationPanel } from "./RestorationPanel";
import { AccessGate } from "./AccessGate";
import { WorkspaceTools } from "./WorkspaceTools";
import "./style.css";
import "./responsive.css";

const navigation = [
  {
    id: "context" as const,
    name: "Company context",
    short: "Context",
    icon: Layers3,
    title: "Good decisions start with context.",
    description:
      "A connected view of your decisions, evidence, and the people behind them.",
  },
  {
    id: "investigation" as const,
    name: "Change investigation",
    short: "Change",
    icon: Activity,
    title: "See the change. Follow the impact.",
    description:
      "From one changed fact to every recorded dependency that needs a second look.",
  },
  {
    id: "queue" as const,
    name: "Follow-up queue",
    short: "Follow-up",
    icon: ListChecks,
    title: "Connected context. Considered action.",
    description:
      "Review the work, bring in the right owners, and keep every decision accountable.",
  },
];
function readView(): View {
  const hash = window.location.hash.slice(1);
  return navigation.some((item) => item.id === hash)
    ? (hash as View)
    : "context";
}
function App({
  account,
  onSignOut,
}: {
  account: RecordData;
  onSignOut: () => void;
}) {
  const [library, setLibrary] = useState(false);
  const [scopeProject, setScopeProject] = useState(
    () =>
      new URLSearchParams(window.location.search).get("project") ||
      "project-atlas",
  );
  const [scopePrerequisite, setScopePrerequisite] = useState(
    () => new URLSearchParams(window.location.search).get("prerequisite") || "",
  );
  const [scopeEvent, setScopeEvent] = useState(
    () => new URLSearchParams(window.location.search).get("event") || "",
  );
  const scopeRef = useRef({
    project: scopeProject,
    prerequisite: scopePrerequisite,
    event: scopeEvent,
  });
  const [view, setView] = useState<View>(readView);
  const [overview, setOverview] = useState<RecordData | null>(null);
  const [ready, setReady] = useState<RecordData | null>(null);
  const [health, setHealth] = useState<RecordData | null>(null);
  const [impact, setImpact] = useState<RecordData | null>(null);
  const [plan, setPlan] = useState<RecordData | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [inspect, setInspect] = useState<RecordData | null>(null);
  const [trail, setTrail] = useState<RecordData[]>([]);
  const [busy, setBusy] = useState("Loading company context");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [command, setCommand] = useState(false);
  const [transition, setTransition] = useState<{
    item: RecordData;
    state: "completed" | "rejected";
  } | null>(null);
  const lock = useRef(false);
  const evidenceSequence = useRef(0);
  const heading = useRef<HTMLHeadingElement>(null);
  const info = navigation.find((item) => item.id === view)!;
  const changed = Boolean(overview?.history.length);
  const openCount =
    overview?.actions.filter(
      (item: RecordData) => item.action.state === "approved",
    ).length || 0;
  async function work(label: string, fn: () => Promise<void>) {
    if (lock.current) return;
    lock.current = true;
    setBusy(label);
    setError("");
    setNotice("");
    try {
      await fn();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      lock.current = false;
      setBusy("");
    }
  }
  async function refresh(
    project = scopeRef.current.project,
    prerequisite = scopeRef.current.prerequisite,
    event = scopeRef.current.event,
  ) {
    const query = "?project_id=" + encodeURIComponent(project);
    const [nextOverview, nextReady, nextHealth] = await Promise.all([
      api(
        "/overview" +
          query +
          (prerequisite
            ? "&prerequisite_id=" + encodeURIComponent(prerequisite)
            : "") +
          (event ? "&event_id=" + encodeURIComponent(event) : ""),
      ),
      api("/readiness" + query),
      api("/health"),
    ]);
    const nextImpact = nextOverview.impact || null;
    setOverview(nextOverview);
    setReady(nextReady);
    setHealth(nextHealth);
    setImpact(nextImpact);
    setScopeProject(project);
    setScopePrerequisite(nextOverview.context.prerequisite_id);
    setScopeEvent(event);
    scopeRef.current = {
      project,
      prerequisite: nextOverview.context.prerequisite_id,
      event,
    };
    const url = new URL(window.location.href);
    url.searchParams.set("project", project);
    if (nextOverview.context.prerequisite_id)
      url.searchParams.set(
        "prerequisite",
        nextOverview.context.prerequisite_id,
      );
    else url.searchParams.delete("prerequisite");
    if (event) url.searchParams.set("event", event);
    else url.searchParams.delete("event");
    window.history.replaceState(null, "", url);
  }
  function navigate(next: View) {
    if (next === view) {
      window.scrollTo({ top: 0 });
      return;
    }
    window.location.hash = next;
  }
  useEffect(() => {
    void work("Loading company context", refresh);
  }, []);
  useEffect(() => {
    const route = () => {
      setView(readView());
      window.scrollTo({ top: 0 });
      requestAnimationFrame(() =>
        heading.current?.focus({ preventScroll: true }),
      );
    };
    const keys = (event: KeyboardEvent) => {
      if (
        (event.ctrlKey || event.metaKey) &&
        event.key.toLowerCase() === "k" &&
        !document.querySelector("dialog[open]")
      ) {
        event.preventDefault();
        setCommand(true);
      }
    };
    window.addEventListener("hashchange", route);
    window.addEventListener("keydown", keys);
    return () => {
      window.removeEventListener("hashchange", route);
      window.removeEventListener("keydown", keys);
    };
  }, []);
  useEffect(() => {
    document.title = `${info.name} · CONTINUUM`;
  }, [info.name]);
  async function open(id: string, nested = false) {
    if (lock.current) return;
    const requestId = ++evidenceSequence.current;
    await work("Loading evidence", async () => {
      const next = await api("/entities/" + encodeURIComponent(id));
      if (requestId !== evidenceSequence.current) return;
      setTrail((previous) => (nested && inspect ? [...previous, inspect] : []));
      setInspect(next);
    });
  }
  function closeEvidence() {
    evidenceSequence.current++;
    setInspect(null);
    setTrail([]);
  }
  function withdraw() {
    void work("Recording synthetic change", async () => {
      if (!overview?.context.prerequisite_id)
        throw new Error(
          "This project has no recorded prerequisite to withdraw.",
        );
      await api("/changes/withdraw", {
        project_id: scopeProject,
        prerequisite_id: overview.context.prerequisite_id,
        expected_revision: overview.revision,
        reason:
          "Synthetic update: " +
          overview.context.active_prerequisite_name +
          " has been withdrawn pending a new authoritative review.",
      });
      await refresh(scopeProject, overview.context.prerequisite_id, "");
      navigate("investigation");
      setNotice(
        "Change persisted. Previous approval remains available in history.",
      );
    });
  }
  function propose() {
    void work("Preparing response plan", async () => {
      if (!overview?.context.event_id)
        throw new Error("Select a recorded change first.");
      const next = await api(
        "/plans?event_id=" + encodeURIComponent(overview.context.event_id),
        {},
      );
      setPlan(next);
      setSelected(
        next.proposals
          .filter((item: RecordData) => item.state === "proposed")
          .map((item: RecordData) => item.id),
      );
      await refresh();
      navigate("queue");
    });
  }
  function approve() {
    if (!plan || !selected.length || plan.revision !== overview?.revision)
      return;
    void work("Creating approved internal tasks", async () => {
      await api("/actions/approve", { plan_id: plan.id, selected });
      setPlan(null);
      setSelected([]);
      await refresh();
      setNotice(
        "Selected internal tasks persisted in FalkorDB. No messages were sent.",
      );
    });
  }
  return (
    <div className="app-shell">
      <a
        className="skip-link"
        href="#main-content"
        onClick={(event) => {
          event.preventDefault();
          document.getElementById("main-content")?.focus();
        }}
      >
        Skip to content
      </a>
      <aside className="sidebar">
        <a className="brand" href="#context" title="CONTINUUM home">
          <span className="brand-icon">
            <GitBranch size={24} />
          </span>
          <span>
            continuum<span className="brand-period">.</span>
            <small>THE CONNECTED COMPANY</small>
          </span>
        </a>
        <div className="company">
          <span className="company-avatar">N</span>
          <div>
            Northstar Systems<small>Fictional company workspace</small>
          </div>
          <Badge>DEMO</Badge>
        </div>
        <span className="nav-label">WORKSPACE</span>
        <nav aria-label="Primary">
          {navigation.map(({ id, name, short, icon: Icon }, index) => (
            <button
              key={id}
              className={`nav ${view === id ? "active" : ""}`}
              aria-current={view === id ? "page" : undefined}
              onClick={() => navigate(id)}
            >
              <Icon size={19} />
              <span className="nav-full">{name}</span>
              <span className="nav-short" aria-hidden="true">
                {short}
              </span>
              {id === "queue" && openCount > 0 ? (
                <span className="nav-count" aria-hidden="true">
                  {openCount}
                </span>
              ) : (
                <span className="nav-index" aria-hidden="true">
                  0{index + 1}
                </span>
              )}
            </button>
          ))}
        </nav>
        <div className="sidebar-guide">
          <span className="section-label">THE CONTEXT LOOP</span>
          <div className="sidebar-loop">
            <span>Evidence</span>
            <ArrowRight size={12} />
            <span>Decision</span>
            <ArrowRight size={12} />
            <span>Action</span>
          </div>
          <p>
            Keep the original reasoning.
            <br />
            Know when it needs another look.
          </p>
          <Button
            variant="text"
            disabled={!overview || !!busy}
            onClick={() =>
              ready?.project.decision_id && void open(ready.project.decision_id)
            }
          >
            Explore a decision <ArrowRight size={14} />
          </Button>
        </div>
        <div className="sidebar-bottom">
          <span className={`status-dot ${overview ? "" : "offline"}`} />
          <span>
            {overview
              ? "FalkorDB connected"
              : busy
                ? "Connecting to graph"
                : "Graph unavailable"}
            <small>
              {overview
                ? `Persistent context · revision ${overview.revision}`
                : "Waiting for company context"}
            </small>
          </span>
          <Database size={16} />
        </div>
        <div className="team">
          OmegaRuby <span>Graph Hacks / Track 3</span>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumb">
            <span>Northstar</span>
            <ChevronRight size={13} />
            <strong>{info.name}</strong>
          </div>
          <div className="topbar-actions">
            <Button variant="text" onClick={() => setLibrary(true)}>
              Workspace library
            </Button>
            {account.mode === "accounts" && (
              <>
                <span className="workspace-label">
                  {account.username} · {account.role} · {account.company}
                </span>
                <Button variant="text" onClick={onSignOut}>
                  Sign out
                </Button>
              </>
            )}
            <button
              className="global-search"
              aria-keyshortcuts="Control+k Meta+k"
              onClick={() => setCommand(true)}
            >
              <Search size={15} />
              <span className="search-label">Search context</span>
              <kbd aria-hidden="true">Ctrl K</kbd>
            </button>
            <span className="workspace-label">
              <span className="status-dot" />
              Local workspace
            </span>
            <button
              className="icon-button"
              aria-label="Refresh persisted state"
              disabled={!!busy}
              onClick={() => void work("Refreshing company context", refresh)}
            >
              <RefreshCw
                size={17}
                className={busy === "Refreshing company context" ? "spin" : ""}
              />
            </button>
          </div>
        </header>
        <main id="main-content" tabIndex={-1}>
          <div className="page-heading">
            <div>
              <div className="eyebrow">
                <span>WORKSPACE / 0{navigation.indexOf(info) + 1}</span>
                <span className="eyebrow-line" />
                {info.name.toUpperCase()}
              </div>
              <h1 ref={heading} tabIndex={-1}>
                {info.title}
              </h1>
              <p>{info.description}</p>
            </div>
            <Badge tone="mint">
              <span className="status-dot" />
              Synthetic data
            </Badge>
          </div>
          {overview && (
            <div
              className="project-context-bar"
              aria-label="Investigation scope"
            >
              <label>
                Project
                <select
                  aria-label="Project"
                  value={scopeProject}
                  disabled={!!busy}
                  onChange={(e) => {
                    const id = e.target.value;
                    void work("Switching project", async () => {
                      await refresh(id, "", "");
                      setPlan(null);
                      setSelected([]);
                      closeEvidence();
                    });
                  }}
                >
                  {overview.projects.map((item: RecordData) => (
                    <option key={item.project.id} value={item.project.id}>
                      {item.project.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Prerequisite
                <select
                  aria-label="Prerequisite"
                  value={scopePrerequisite}
                  disabled={!!busy || !overview.prerequisites.length}
                  onChange={(e) => {
                    const id = e.target.value;
                    void work("Switching prerequisite", async () => {
                      await refresh(scopeProject, id, "");
                      setPlan(null);
                      setSelected([]);
                      closeEvidence();
                    });
                  }}
                >
                  {!overview.prerequisites.length && (
                    <option value="">No recorded prerequisite</option>
                  )}
                  {overview.prerequisites.map((item: RecordData) => (
                    <option key={item.id} value={item.id}>
                      {item.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Incident history
                <select
                  aria-label="Incident history"
                  value={scopeEvent}
                  disabled={!!busy}
                  onChange={(e) => {
                    const id = e.target.value;
                    void work("Loading incident history", async () => {
                      await refresh(scopeProject, scopePrerequisite, id);
                      setPlan(null);
                      setSelected([]);
                      closeEvidence();
                    });
                  }}
                >
                  <option value="">
                    Latest incident for current prerequisite
                  </option>
                  {overview.project_history.map((item: RecordData) => (
                    <option key={item.event.id} value={item.event.id}>
                      {item.event.cycle_index
                        ? "Cycle " + item.event.cycle_index + " · "
                        : ""}
                      {item.event.state} ·{" "}
                      {new Date(item.created_at).toLocaleString()} ·{" "}
                      {item.previous.name}
                    </option>
                  ))}
                </select>
              </label>
              <small>
                Evidence, changes and review are scoped to your selection.
                {overview.history_truncated &&
                  " Latest 100 incidents shown; older records remain accessible by event ID."}
              </small>
            </div>
          )}
          <div className="feedback-region">
            {busy && overview && (
              <div className="message loading" role="status">
                <LoaderCircle className="spin" size={16} />
                {busy}…
              </div>
            )}
            {error && (
              <div className="message error" role="alert">
                <TriangleAlert size={18} />
                <span>{error}</span>
                <Button
                  variant="text"
                  disabled={!!busy}
                  onClick={() =>
                    void work("Refreshing company context", refresh)
                  }
                >
                  Refresh context
                </Button>
                <CloseButton
                  label="Dismiss error"
                  onClick={() => setError("")}
                />
              </div>
            )}
            {notice && (
              <div className="message success" role="status">
                <Check size={18} />
                <span>{notice}</span>
                <CloseButton
                  label="Dismiss notification"
                  onClick={() => setNotice("")}
                />
              </div>
            )}
          </div>
          {!overview &&
            (busy ? (
              <div
                className="loading-workspace"
                role="status"
                aria-label="Loading company context"
              >
                <span className="loading-label">
                  <LoaderCircle className="spin" size={16} />
                  Connecting your company context…
                </span>
                <div className="skeleton skeleton-stats" />
                <div className="skeleton-grid">
                  <div className="skeleton" />
                  <div className="skeleton" />
                </div>
              </div>
            ) : (
              <section className="panel">
                <EmptyState
                  icon={<Database size={28} />}
                  title="Your company context is unavailable."
                  action={
                    <Button
                      onClick={() =>
                        void work("Connecting to FalkorDB", refresh)
                      }
                    >
                      Retry connection
                    </Button>
                  }
                >
                  Start FalkorDB and import the synthetic company fixture, then
                  retry the connection.
                </EmptyState>
              </section>
            ))}
          {overview && ready && (
            <>
              <div hidden={view !== "context"}>
                <ContextPage
                  key={
                    scopeProject + ":" + scopePrerequisite + ":" + scopeEvent
                  }
                  overview={overview}
                  ready={ready}
                  impact={impact}
                  configured={!!health?.agent_configured}
                  busy={busy}
                  work={work}
                  onInspect={(id) => void open(id)}
                  onNavigate={navigate}
                  onWithdraw={withdraw}
                />
              </div>
              <div hidden={view !== "investigation"}>
                <InvestigationPage
                  overview={overview}
                  changed={changed}
                  impact={impact}
                  ready={ready}
                  busy={busy}
                  onInspect={(id) => void open(id)}
                  onPropose={propose}
                  onWithdraw={withdraw}
                />
                <RestorationPanel
                  key={
                    scopeProject +
                    ":" +
                    scopePrerequisite +
                    ":" +
                    overview.context.event_id
                  }
                  overview={overview}
                  busy={busy}
                  work={work}
                  onRefresh={refresh}
                  onInspect={(id) => void open(id)}
                  onQueue={() => navigate("queue")}
                />
              </div>
              <div hidden={view !== "queue"}>
                <QueuePage
                  overview={overview}
                  plan={plan}
                  selected={selected}
                  setSelected={setSelected}
                  busy={busy}
                  onReview={(next) => {
                    setPlan(next);
                    setSelected(
                      next.proposals
                        .filter((item: RecordData) => item.state === "proposed")
                        .map((item: RecordData) => item.id),
                    );
                    window.scrollTo({ top: 0 });
                  }}
                  onPropose={propose}
                  onApprove={approve}
                  onInspect={(id) => void open(id)}
                  onInvestigate={() => navigate("investigation")}
                  onTransition={(item, state) => setTransition({ item, state })}
                />
              </div>
              <footer className="main-footer">
                <span>
                  <GitBranch size={14} />
                  CONTINUUM <span>/</span> Team OmegaRuby
                </span>
                <span>Fictional company. Real graph. Considered actions.</span>
              </footer>
            </>
          )}
        </main>
      </div>
      {inspect && (
        <EvidenceDrawer
          data={inspect}
          busy={!!busy}
          error={error}
          onClose={closeEvidence}
          onInspect={(id) => void open(id, true)}
          onBack={
            trail.length
              ? () => {
                  setInspect(trail[trail.length - 1]);
                  setTrail(trail.slice(0, -1));
                }
              : undefined
          }
        />
      )}
      {command && (
        <CommandSearch
          onClose={() => setCommand(false)}
          onInspect={(id) => void open(id)}
          onNavigate={navigate}
        />
      )}
      {transition && (
        <Modal
          label={
            transition.state === "rejected"
              ? "Reject follow-up"
              : "Complete follow-up"
          }
          onClose={() => {
            if (!busy) setTransition(null);
          }}
          className="confirm-dialog"
        >
          <div className="confirm-heading">
            <span className="small-icon">
              {transition.state === "rejected" ? (
                <X size={22} />
              ) : (
                <Check size={22} />
              )}
            </span>
            <CloseButton
              onClick={() => {
                if (!busy) setTransition(null);
              }}
            />
          </div>
          <h2>
            {transition.state === "rejected"
              ? "Reject this follow-up?"
              : "Mark this work complete?"}
          </h2>
          {error && (
            <p className="inline-error" role="alert">
              {error}
            </p>
          )}
          <p className="confirm-task">{transition.item.action.name}</p>
          <p>
            {transition.state === "rejected"
              ? "This records the task as rejected and keeps its evidence trail."
              : "This records the internal task as completed."}{" "}
            Completing this task does not change the prerequisite approval.
          </p>
          <div className="confirm-actions">
            <Button
              variant="secondary"
              disabled={!!busy}
              onClick={() => setTransition(null)}
            >
              Keep open
            </Button>
            <Button
              variant={transition.state === "rejected" ? "danger" : "primary"}
              disabled={!!busy}
              onClick={() => {
                const pending = transition;
                void work("Updating internal follow-up", async () => {
                  await api(
                    "/actions/" + pending.item.action.id,
                    { state: pending.state },
                    "PATCH",
                  );
                  await refresh();
                  setTransition(null);
                  setNotice(
                    pending.state === "rejected"
                      ? "Follow-up rejected. Its evidence and history are retained."
                      : "Follow-up completed. Prerequisite approval still needs review.",
                  );
                });
              }}
            >
              {transition.state === "rejected"
                ? "Reject follow-up"
                : "Mark complete"}
            </Button>
          </div>
        </Modal>
      )}
      {library && (
        <WorkspaceTools
          account={account}
          projectId={scopeProject}
          onClose={() => setLibrary(false)}
          onInspect={(id) => {
            setLibrary(false);
            void open(id);
          }}
          onImported={refresh}
          onIncident={async (id) => {
            await refresh(scopeProject, "", id);
            setView("investigation");
            window.location.hash = "investigation";
            setPlan(null);
            setSelected([]);
          }}
        />
      )}
    </div>
  );
}
createRoot(document.getElementById("root")!).render(
  <AccessGate>
    {(account, onSignOut) => <App account={account} onSignOut={onSignOut} />}
  </AccessGate>,
);
