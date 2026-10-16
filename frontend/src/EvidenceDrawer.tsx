import { ArrowLeft, ArrowRight, GitBranch } from "lucide-react";
import {
  Badge,
  Button,
  CloseButton,
  Modal,
  Source,
  type RecordData,
} from "./ui";

export function EvidenceDrawer({
  data,
  onClose,
  onInspect,
  onBack,
  busy,
  error,
}: {
  data: RecordData;
  onClose: () => void;
  onInspect: (id: string) => void;
  onBack?: () => void;
  busy: boolean;
  error: string;
}) {
  const entity = data.entity;
  return (
    <Modal
      label="Entity evidence"
      onClose={onClose}
      className="evidence-drawer"
    >
      {error && (
        <p className="inline-error" role="alert">
          {error}
        </p>
      )}
      <div className="drawer-top">
        <span className="eyebrow">
          <GitBranch size={14} /> EVIDENCE EXPLORER
        </span>
        <CloseButton label="Close evidence" onClick={onClose} />
      </div>
      {onBack && (
        <Button variant="text" onClick={onBack} disabled={busy}>
          <ArrowLeft size={14} /> Back to previous evidence
        </Button>
      )}
      <div className="drawer-heading" aria-busy={busy}>
        <Badge tone="mint">{entity.kind}</Badge>
        <h2>{entity.name}</h2>
        <code>{entity.id}</code>
      </div>
      <div className="entity-meta">
        {entity.state && (
          <Badge
            tone={
              ["superseded", "withdrawn", "rejected"].includes(entity.state)
                ? "amber"
                : "neutral"
            }
          >
            {entity.state}
          </Badge>
        )}
        <Badge>{entity.classification || "Curated source"}</Badge>
        {entity.current === false && (
          <Badge tone="amber">Historical record</Badge>
        )}
      </div>
      {entity.kind === "RestorationReview" && entity.note && (
        <section className="evidence-section">
          <h3>Revalidation rationale</h3>
          <p>{entity.note}</p>
          <p>
            Synthetic reviewer ID: <code>{entity.reviewer_id}</code>
          </p>
          <p>
            {entity.reviewed_targets?.length || 0} affected items reviewed ·{" "}
            {new Date(entity.reviewed_at).toLocaleString()}
          </p>
        </section>
      )}
      {entity.excerpt && <blockquote>{entity.excerpt}</blockquote>}
      {entity.version && (
        <dl className="version-meta">
          <div>
            <dt>Version</dt>
            <dd>{entity.version}</dd>
          </div>
          <div>
            <dt>Effective</dt>
            <dd>{entity.valid_from}</dd>
          </div>
          <div>
            <dt>Authority</dt>
            <dd>{entity.authority}</dd>
          </div>
        </dl>
      )}
      {data.ownership.records.length > 0 && (
        <section>
          <div className="section-heading">
            <h3>Accountable owner</h3>
            {data.ownership.conflict && (
              <Badge tone="amber">Conflict surfaced</Badge>
            )}
          </div>
          <p className="muted">
            Current owner:{" "}
            <strong>{data.ownership.owner?.name || "Unresolved"}</strong>
          </p>
          {data.ownership.records.map((record: RecordData, i: number) => (
            <div className="ownership-record" key={i}>
              <div>
                <strong>{record.person.name}</strong>
                <small>
                  {record.record.current ? "Current" : "Historical"} · authority{" "}
                  {record.record.authority}
                </small>
              </div>
              <Button
                variant="text"
                onClick={() => onInspect(record.record.source)}
                disabled={busy}
              >
                Resolution source <ArrowRight size={14} />
              </Button>
            </div>
          ))}
        </section>
      )}
      <section>
        <div className="section-heading">
          <h3>Source excerpts & versions</h3>
          <span className="count-label">{data.evidence.length}</span>
        </div>
        {data.evidence.length ? (
          data.evidence.map((record: RecordData, i: number) => (
            <div key={i} className="evidence-card">
              <Source source={record.version} onInspect={onInspect} />
              <blockquote>{record.version.excerpt}</blockquote>
              <small className="muted">
                v{record.version.version} · {record.version.valid_from} ·{" "}
                {record.version.authority}
              </small>
            </div>
          ))
        ) : (
          <p className="muted">
            {entity.excerpt
              ? "This immutable version is the source."
              : "No direct evidence is recorded. Inspect the relationships below; missing evidence is not proof of safety."}
          </p>
        )}
      </section>
      <section>
        <div className="section-heading">
          <h3>Connected relationships</h3>
          <span className="count-label">{data.relationships.length}</span>
        </div>
        {data.relationships.length ? (
          data.relationships.map((record: RecordData, i: number) => (
            <div className="relationship" key={i}>
              <small>
                {record.from_id === entity.id ? "Outgoing" : "Incoming"} ·{" "}
                {record.relation.replaceAll("_", " ")}
              </small>
              <button
                disabled={busy}
                onClick={() => onInspect(record.entity.id)}
              >
                {record.entity.name || record.entity.id}
                <ArrowRight size={15} />
              </button>
              {record.edge.source && (
                <Button
                  variant="text"
                  disabled={busy}
                  onClick={() => onInspect(record.edge.source)}
                >
                  Inspect edge evidence
                </Button>
              )}
            </div>
          ))
        ) : (
          <p className="muted">
            No relationships are recorded for this entity.
          </p>
        )}
      </section>
    </Modal>
  );
}
