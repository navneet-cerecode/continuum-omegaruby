import { useState } from "react";
import { ArrowRight, GitBranch, ListChecks, Sparkles } from "lucide-react";
import {
  api,
  Badge,
  Button,
  CloseButton,
  PathView,
  type RecordData,
} from "./ui";

export type Work = (label: string, fn: () => Promise<void>) => Promise<void>;
export function AskPanel({
  ready,
  eventId,
  configured,
  busy,
  work,
  onInspect,
}: {
  ready: RecordData;
  eventId?: string;
  configured: boolean;
  busy: string;
  work: Work;
  onInspect: (id: string) => void;
}) {
  const [question, setQuestion] = useState(
    "Are we ready to launch " +
      ready.project.name +
      ", and what supports that answer?",
  );
  const [answer, setAnswer] = useState<RecordData | null>(null);
  return (
    <section className="ask-panel panel" aria-labelledby="ask-title">
      <div className="ask-heading">
        <span className="ask-icon">
          <Sparkles size={19} />
        </span>
        <div>
          <h2 id="ask-title">A question. A connected answer.</h2>
          <p>Explore the graph, with the evidence always in reach.</p>
        </div>
        <Badge tone={configured ? "mint" : "neutral"}>
          {configured ? "Agent configured" : "Graph exploration"}
        </Badge>
      </div>
      <form
        className="ask-form"
        onSubmit={(e) => {
          e.preventDefault();
          if (!configured || question.trim().length < 3) return;
          void work("Investigating company context", async () =>
            setAnswer(
              await api("/agent", {
                question: question.trim(),
                project_id: ready.project.id,
                ...(eventId ? { event_id: eventId } : {}),
              }),
            ),
          );
        }}
      >
        <label className="sr-only" htmlFor="agent-question">
          Question for the company brain
        </label>
        <textarea
          id="agent-question"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          minLength={3}
          maxLength={1500}
          rows={2}
          required
        />
        <Button
          type="submit"
          disabled={!!busy || !configured || question.trim().length < 3}
          loading={busy === "Investigating company context"}
        >
          <Sparkles size={15} /> Ask agent
        </Button>
      </form>
      {!configured && (
        <p className="agent-help">
          Model inference is unavailable. You can still explore readiness and
          recorded changes below.
        </p>
      )}
      <div className="ask-options">
        <span className="section-label">EXPLORE DIRECTLY</span>
        <button
          disabled={!!busy}
          onClick={() => setAnswer({ mode: "deterministic", answer: ready })}
        >
          Explore launch readiness <ArrowRight size={14} />
        </button>
        <button
          disabled={!!busy}
          onClick={() =>
            void work("Reading persisted history", async () => {
              setAnswer({
                mode: "deterministic",
                answer: await api(
                  (eventId
                    ? "/events/" + encodeURIComponent(eventId)
                    : "/recap") +
                    "?project_id=" +
                    encodeURIComponent(ready.project.id),
                ),
              });
              setQuestion(
                "What changed, why was the launch flagged, and what remains unresolved?",
              );
            })
          }
        >
          What changed? <ArrowRight size={14} />
        </button>
      </div>
      {answer && (
        <div className="answer" aria-live="polite">
          <div className="answer-heading">
            <Badge tone="mint">
              <GitBranch size={12} />
              {answer.mode === "agent"
                ? "MODEL + GRAPH"
                : "DETERMINISTIC GRAPH EXPLORATION"}
            </Badge>
            <CloseButton label="Close answer" onClick={() => setAnswer(null)} />
          </div>
          <h3>{answer.answer.conclusion}</h3>
          {answer.answer.next_step && <p>{answer.answer.next_step}</p>}
          {answer.answer.caveat && (
            <p className="muted">{answer.answer.caveat}</p>
          )}
          {answer.mode === "agent" ? (
            <>
              <p className="muted">{answer.grounding_note}</p>
              {answer.open_followups?.length > 0 && (
                <div className="recorded-followups">
                  <h4>Unresolved internal follow-ups</h4>
                  {answer.open_followups.map((item: RecordData) => (
                    <button
                      className="source"
                      key={item.action.id}
                      onClick={() => onInspect(item.action.id)}
                    >
                      <ListChecks size={17} />
                      <span>
                        {item.action.name}
                        <small>
                          {item.owner} · {item.action.state}
                        </small>
                      </span>
                      <ArrowRight size={15} />
                    </button>
                  ))}
                </div>
              )}
              {answer.answer.conflicts.map((conflict: string, i: number) => (
                <p className="conflict-note" key={i}>
                  Model interpretation — review against sources: {conflict}
                </p>
              ))}
              {answer.citation_check && (
                <details>
                  <summary>Check evidence coverage</summary>
                  <p>
                    {answer.citation_check.model_citation_coverage_complete
                      ? "The model cited the recorded sources for its selected paths and assessment."
                      : "Application checks attached sources the model omitted. Inspect them before relying on its interpretation."}{" "}
                    Prose entailment remains unverified.
                  </p>
                  {answer.citation_check.source_excerpts.map(
                    (source: RecordData) => (
                      <div key={source.id}>
                        <button
                          className="evidence-link"
                          onClick={() => onInspect(source.id)}
                        >
                          {source.id}
                        </button>
                        <p>{source.excerpt}</p>
                      </div>
                    ),
                  )}
                </details>
              )}
              {answer.answer.supporting_paths.map(
                (path: string[], i: number) => (
                  <PathView key={i} path={path} onInspect={onInspect} />
                ),
              )}
              <div className="answer-sources">
                {answer.answer.source_ids.map((id: string) => (
                  <button
                    className="chip"
                    key={id}
                    onClick={() => onInspect(id)}
                  >
                    {id}
                  </button>
                ))}
              </div>
              <details>
                <summary>
                  Tool activity · {answer.trace.length} calls ·{" "}
                  {Math.round(answer.model_ms)} ms
                </summary>
                {answer.trace.map((trace: RecordData, i: number) => (
                  <details key={i}>
                    <summary>
                      {trace.tool} · {trace.duration_ms} ms
                    </summary>
                    <pre>{JSON.stringify(trace, null, 2)}</pre>
                  </details>
                ))}
              </details>
            </>
          ) : (
            <>
              {(answer.answer.paths || []).map(
                (item: RecordData, i: number) => (
                  <PathView key={i} path={item.path} onInspect={onInspect} />
                ),
              )}
              {answer.answer.impact?.items.map((item: RecordData) => (
                <PathView
                  key={item.id}
                  path={item.path}
                  onInspect={onInspect}
                />
              ))}
              {answer.answer.actions?.length > 0 && (
                <p className="muted">
                  {answer.answer.actions.length} persisted follow-ups are
                  included in this recap.
                </p>
              )}
              <details>
                <summary>Inspect complete grounded response</summary>
                <pre>{JSON.stringify(answer.answer, null, 2)}</pre>
              </details>
              <p className="exploration-note">
                Direct graph exploration · This answer did not run an LLM.
              </p>
            </>
          )}
        </div>
      )}
    </section>
  );
}
