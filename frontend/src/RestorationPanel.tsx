import { useState } from "react";
import { ArrowRight, Check, RefreshCw, ShieldCheck } from "lucide-react";
import { api, Badge, Button, Source, type RecordData } from "./ui";
import { type Work } from "./AskPanel";

export function RestorationPanel({
  overview,
  busy,
  work,
  onRefresh,
  onInspect,
  onQueue,
}: {
  overview: RecordData;
  busy: string;
  work: Work;
  onRefresh: () => Promise<void>;
  onInspect: (id: string) => void;
  onQueue: () => void;
}) {
  const [snapshot, setSnapshot] = useState<RecordData | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [note, setNote] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [attested, setAttested] = useState(false);
  const [title, setTitle] = useState(
    "Synthetic replacement review: " + overview.context.prerequisite_name,
  );
  const [reference, setReference] = useState("REVIEW-42");
  const [excerpt, setExcerpt] = useState(
    "Synthetic review passed. The recorded controls were rechecked, and " +
      overview.context.prerequisite_name +
      " is approved for the reviewed scope.",
  );
  const event = overview.history.find(
    (item: RecordData) => item.event.id === overview.context.event_id,
  )?.event;
  const resolved = event?.state === "resolved";
  const stale = snapshot && snapshot.revision !== overview.revision;
  const reviewer = snapshot?.candidate_readiness.owner_resolution.owner;
  const candidates = overview.restorations || [];
  const active = resolved
    ? candidates.find(
        (item: RecordData) => item.review.id === event.restoration_review_id,
      )
    : null;
  function resetReview(next: RecordData) {
    setSnapshot(next);
    setSelected([]);
    setConfirmed(false);
    setNote("");
  }
  function load(id: string) {
    void work("Preparing replacement approval review", async () => {
      const next = await api("/restorations/" + id);
      await onRefresh();
      resetReview(next);
    });
  }
  if (!event) return null;
  return (
    <section
      className="panel restoration-panel"
      aria-labelledby="restoration-title"
    >
      <div className="panel-heading">
        <div>
          <span className="section-label">
            EVIDENCE → REVALIDATION → RESOLUTION
          </span>
          <h2 id="restoration-title">
            {resolved
              ? "Approval restored. History retained."
              : "Bring the decision back into review."}
          </h2>
          <p>
            {resolved
              ? "Replacement evidence and explicit revalidation resolved the withdrawal. Final launch sign-off remains with the launch lead."
              : "Record replacement approval evidence, close open follow-ups, and explicitly review every affected item."}
          </p>
        </div>
        <Badge tone={resolved ? "mint" : "amber"}>
          {resolved ? "Resolved" : "Human review required"}
        </Badge>
      </div>
      {resolved ? (
        <div className="restoration-body">
          <p className="message success" role="status">
            <Check size={18} /> Withdrawal resolved through explicit
            revalidation.
          </p>
          {active && (
            <>
              <Source
                source={{
                  id: active.source_id,
                  name: "Replacement approval evidence",
                }}
                onInspect={onInspect}
              />
              <Button
                variant="text"
                onClick={() => onInspect(active.review.id)}
              >
                Inspect revalidation record <ArrowRight size={14} />
              </Button>
            </>
          )}
          <p>
            Recorded resolution: {new Date(event.resolved_at).toLocaleString()}.
            Original approval, withdrawal, dependencies and follow-up records
            remain available.
          </p>
        </div>
      ) : (
        <div className="restoration-body">
          <details className="replacement-entry" open={!candidates.length}>
            <summary>Record replacement approval evidence</summary>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (!attested || busy) return;
                void work(
                  "Recording synthetic replacement evidence",
                  async () => {
                    const next = await api("/restorations", {
                      expected_revision: overview.revision,
                      title,
                      reference,
                      excerpt,
                      synthetic: true,
                      approval_confirmed: true,
                      event_id: event.id,
                    });
                    await onRefresh();
                    resetReview(next);
                    setAttested(false);
                  },
                );
              }}
            >
              <p>
                Fictional Northstar Systems scenario. This records a synthetic
                approval review; it does not authorize a real launch.
              </p>
              <label>
                Review title
                <input
                  required
                  minLength={5}
                  maxLength={200}
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                />
              </label>
              <label>
                Review reference
                <input
                  required
                  minLength={3}
                  maxLength={80}
                  value={reference}
                  onChange={(e) => setReference(e.target.value)}
                />
              </label>
              <label>
                Replacement evidence excerpt
                <textarea
                  required
                  minLength={20}
                  maxLength={6000}
                  rows={4}
                  value={excerpt}
                  onChange={(e) => setExcerpt(e.target.value)}
                />
              </label>
              <label className="review-check">
                <input
                  type="checkbox"
                  checked={attested}
                  onChange={(e) => setAttested(e.target.checked)}
                />
                I confirm this synthetic review explicitly approves the selected
                prerequisite.
              </label>
              <Button type="submit" disabled={!!busy || !attested}>
                Record evidence for review <ArrowRight size={15} />
              </Button>
            </form>
          </details>
          {candidates.length > 0 && (
            <div className="replacement-history">
              {candidates.map((item: RecordData) => (
                <div key={item.review.id}>
                  <span>
                    Replacement review ·{" "}
                    {new Date(item.review.created_at).toLocaleString()}
                  </span>
                  <Button
                    variant="secondary"
                    disabled={!!busy}
                    onClick={() => load(item.review.id)}
                  >
                    Review replacement approval
                  </Button>
                </div>
              ))}
            </div>
          )}
          {snapshot && (
            <div
              className="replacement-review"
              aria-label="Replacement approval review"
            >
              <div className="review-heading">
                <h3>Review the evidence and affected items.</h3>
                <Button
                  variant="text"
                  disabled={!!busy}
                  onClick={() => load(snapshot.review.id)}
                >
                  <RefreshCw size={14} /> Refresh review
                </Button>
              </div>
              <Source source={snapshot.source} onInspect={onInspect} />
              <blockquote>{snapshot.source.excerpt}</blockquote>
              <p>
                <strong>
                  Projected readiness: {snapshot.candidate_readiness.status}.
                </strong>{" "}
                This preview has not changed the active approval.
              </p>
              {stale && (
                <p className="message error" role="alert">
                  Context changed. Refresh this review and confirm the affected
                  items again.
                </p>
              )}
              {snapshot.blockers.length > 0 && (
                <div className="review-blockers" role="status">
                  <strong>Resolve before approval</strong>
                  <ul>
                    {snapshot.blockers.map((message: string) => (
                      <li key={message}>{message}</li>
                    ))}
                  </ul>
                  {snapshot.open_actions.length > 0 && (
                    <Button variant="text" onClick={onQueue}>
                      Open follow-up queue <ArrowRight size={14} />
                    </Button>
                  )}
                  {snapshot.candidate_readiness.issues.length > 0 && (
                    <ul>
                      {snapshot.candidate_readiness.issues.map(
                        (issue: RecordData, i: number) => (
                          <li key={i}>{issue.message}</li>
                        ),
                      )}
                    </ul>
                  )}
                </div>
              )}
              <fieldset disabled={!!busy || !!stale || !snapshot.can_approve}>
                <legend>
                  Confirm each affected item ({selected.length}/
                  {snapshot.impact.items.length})
                </legend>
                {snapshot.impact.items.map((item: RecordData) => (
                  <label className="review-check" key={item.id}>
                    <input
                      type="checkbox"
                      checked={selected.includes(item.id)}
                      onChange={(e) =>
                        setSelected((previous) =>
                          e.target.checked
                            ? [...previous, item.id]
                            : previous.filter((id) => id !== item.id),
                        )
                      }
                    />
                    <span>
                      {item.name}
                      <small>
                        {item.kind} · Current owner:{" "}
                        {item.owner_resolution.owner?.name || "Unresolved"}
                      </small>
                    </span>
                  </label>
                ))}
                <label>
                  Revalidation rationale
                  <textarea
                    minLength={10}
                    maxLength={2000}
                    rows={3}
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    placeholder="Explain why the replacement evidence supports these dependencies."
                  />
                </label>
                <p>
                  Synthetic reviewer:{" "}
                  <strong>{reviewer?.name || "Unresolved launch owner"}</strong>
                  . This local demo records the selected role; it has no
                  authenticated identity.
                </p>
                <label className="review-check">
                  <input
                    type="checkbox"
                    checked={confirmed}
                    onChange={(e) => setConfirmed(e.target.checked)}
                  />
                  I reviewed the replacement evidence and every affected item in
                  this synthetic launch-owner role.
                </label>
              </fieldset>
              <Button
                disabled={
                  !!busy ||
                  !!stale ||
                  !snapshot.can_approve ||
                  !confirmed ||
                  selected.length !== snapshot.impact.items.length ||
                  note.trim().length < 10
                }
                onClick={() => {
                  void work(
                    "Revalidating dependencies and resolving withdrawal",
                    async () => {
                      await api(
                        "/restorations/" + snapshot.review.id + "/approve",
                        {
                          expected_revision: snapshot.revision,
                          fingerprint: snapshot.fingerprint,
                          reviewer_id: reviewer.id,
                          reviewed_targets: selected,
                          note,
                          confirm: true,
                        },
                      );
                      await onRefresh();
                      setSnapshot(null);
                      setSelected([]);
                      setConfirmed(false);
                    },
                  );
                }}
              >
                <ShieldCheck size={16} /> Revalidate and resolve withdrawal
              </Button>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
