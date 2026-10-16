import { useEffect, useRef, useState } from "react";
import { api, Button, CloseButton, Modal, type RecordData } from "./ui";

const template =
  "---json\n" +
  JSON.stringify(
    {
      id: "doc-new-review-v1",
      document_id: "doc-new-review",
      title: "Synthetic review",
      version: 1,
      valid_from: "2026-10-17T01:00:00Z",
      authority: "product",
      synthetic: true,
      subjects: ["project-atlas"],
    },
    null,
    2,
  ) +
  "\n---\nEnter the actual synthetic source excerpt here. Subject IDs are explicit human mappings.";

export function WorkspaceTools({
  account,
  projectId,
  onClose,
  onInspect,
  onIncident,
  onImported,
}: {
  account: RecordData;
  projectId: string;
  onClose: () => void;
  onInspect: (id: string) => void;
  onIncident: (id: string) => Promise<void>;
  onImported: () => Promise<void>;
}) {
  const [tab, setTab] = useState("records");
  const [kind, setKind] = useState("history");
  const [scoped, setScoped] = useState(true);
  const [items, setItems] = useState<RecordData[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [markdown, setMarkdown] = useState<string[]>([template]);
  const [preview, setPreview] = useState<RecordData | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const pageRequest = useRef<AbortController | null>(null);
  const canImport = account.mode === "demo" || account.role === "admin";
  async function work(fn: () => Promise<void>) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await fn();
    } catch (e) {
      if (!(e instanceof DOMException && e.name === "AbortError")) setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setBusy(false);
    }
  }
  async function load(next: string | null = null) {
    pageRequest.current?.abort();
    const request = new AbortController();
    pageRequest.current = request;
    const params = new URLSearchParams({ limit: "25" });
    if (scoped && kind !== "sources") params.set("project_id", projectId);
    if (next) params.set("cursor", next);
    const data = await api("/records/" + kind + "?" + params, undefined, undefined, request.signal);
    if (request.signal.aborted) return;
    setItems((old) => (next ? [...old, ...data.items] : data.items));
    setCursor(data.next_cursor);
  }
  useEffect(() => {
    setItems([]);
    setCursor(null);
    void work(() => load());
    return () => pageRequest.current?.abort();
  }, [kind, scoped, projectId]);
  return (
    <Modal
      onClose={onClose}
      label="Workspace library"
      className="library-modal"
    >
      <div className="modal-top">
        <span className="section-label">WORKSPACE LIBRARY</span>
        <CloseButton label="Close workspace library" onClick={onClose} />
      </div>
      <h2>Evidence and recorded work.</h2>
      <div className="library-tabs">
        <Button
          variant={tab === "records" ? "primary" : "secondary"}
          onClick={() => setTab("records")}
        >
          Browse records
        </Button>
        {canImport && (
          <Button
            variant={tab === "sources" ? "primary" : "secondary"}
            onClick={() => setTab("sources")}
          >
            Import sources
          </Button>
        )}
      </div>
      {error && (
        <p className="inline-error" role="alert">
          {error}
        </p>
      )}
      {notice && (
        <p className="message success" role="status">
          {notice}
        </p>
      )}
      {tab === "records" ? (
        <>
          <div className="library-filters">
            <label>
              Record type
              <select
                aria-label="Record type"
                value={kind}
                disabled={busy}
                onChange={(e) => setKind(e.target.value)}
              >
                <option value="history">Incidents</option>
                <option value="actions">Follow-ups</option>
                <option value="plans">Response plans</option>
                <option value="restorations">Revalidation reviews</option>
                <option value="sources">Source versions</option>
              </select>
            </label>
            {kind !== "sources" && (
              <label>
                <input
                  type="checkbox"
                  checked={scoped}
                  onChange={(e) => setScoped(e.target.checked)}
                />{" "}
                Selected project only
              </label>
            )}
            <Button
              variant="secondary"
              disabled={busy}
              onClick={() => void work(() => load())}
            >
              Restart browsing
            </Button>
          </div>
          <p className="muted">
            Pages contain up to 25 records. If records change while browsing,
            restart to see a consistent revision.
          </p>
          <div className="library-records">
            {items.map((item) => (
              <article key={item.id}>
                <div>
                  <strong>{item.name}</strong>
                  <p>
                    {item.state ||
                      (item.current
                        ? "Current source"
                        : "Historical source")}{" "}
                    ·{" "}
                    {item.created_at || item.valid_from || "Date not recorded"}
                  </p>
                  <small>{item.id}</small>
                </div>
                <Button variant="text" onClick={() => onInspect(item.id)}>
                  Inspect evidence
                </Button>
                {kind === "history" && scoped && (
                  <Button
                    variant="secondary"
                    onClick={() =>
                      void work(async () => {
                        await onIncident(item.id);
                        onClose();
                      })
                    }
                  >
                    Open incident
                  </Button>
                )}
              </article>
            ))}
            {!busy && !items.length && <p>No records in this scope.</p>}
          </div>
          {cursor && (
            <Button
              disabled={busy}
              loading={busy}
              onClick={() => void work(() => load(cursor))}
            >
              Load older records
            </Button>
          )}
        </>
      ) : (
        <>
          <p>
            Import up to five synthetic Markdown sources (24KB combined). Map
            them to existing subject IDs explicitly. Importing a source never
            creates a dependency, changes an owner, or grants approval.
          </p>
          <label>
            Choose Markdown files
            <input
              aria-label="Choose Markdown files"
              type="file"
              accept=".md,text/markdown"
              multiple
              disabled={busy}
              onChange={(e) => {
                const files = Array.from(e.target.files || []);
                void work(async () => {
                  if (
                    !files.length ||
                    files.length > 5 ||
                    files.reduce((n, f) => n + f.size, 0) > 24000
                  )
                    throw new Error(
                      "Choose one to five files, up to 24KB combined",
                    );
                  setMarkdown(await Promise.all(files.map((f) => f.text())));
                  setPreview(null);
                  setConfirmed(false);
                });
              }}
            />
          </label>
          {markdown.map((text, i) => (
            <label key={i}>
              Markdown source {i + 1}
              <textarea
                aria-label={"Markdown source " + (i + 1)}
                className="source-editor"
                value={text}
                disabled={busy}
                onChange={(e) => {
                  setMarkdown((old) =>
                    old.map((v, n) => (n === i ? e.target.value : v)),
                  );
                  setPreview(null);
                  setConfirmed(false);
                }}
              />
            </label>
          ))}
          <Button
            disabled={busy}
            loading={busy}
            onClick={() =>
              void work(async () => {
                setPreview(await api("/sources/preview", { markdown }));
                setConfirmed(false);
              })
            }
          >
            Preview sources
          </Button>
          {preview && (
            <section className="source-preview">
              <h3>Review the complete batch</h3>
              {preview.sources.map((item: RecordData) => (
                <article key={item.metadata.id}>
                  <strong>{item.metadata.title}</strong>
                  <p>
                    {item.metadata.id} · {item.metadata.authority} ·{" "}
                    {item.metadata.valid_from}
                  </p>
                  <p>
                    Subjects:{" "}
                    {item.metadata.subjects.join(", ") || "No subjects"}
                  </p>
                  <pre>{item.excerpt}</pre>
                  {item.already_imported && <p>Already imported; no change.</p>}
                </article>
              ))}
              <p>{preview.mapping}</p>
              <label>
                <input
                  type="checkbox"
                  checked={confirmed}
                  onChange={(e) => setConfirmed(e.target.checked)}
                />{" "}
                I reviewed the excerpts, authority, dates and subject mappings.
              </label>
              <Button
                disabled={busy || !confirmed}
                loading={busy}
                onClick={() =>
                  void work(async () => {
                    const result = await api("/sources/import", {
                      markdown,
                      expected_revision: preview.revision,
                      fingerprint: preview.fingerprint,
                    });
                    setPreview(null);
                    setConfirmed(false);
                    await onImported();
                    setNotice(
                      result.imported +
                        " source versions imported. Existing decisions and dependencies retain their original evidence.",
                    );
                  })
                }
              >
                Import reviewed batch
              </Button>
            </section>
          )}
        </>
      )}
    </Modal>
  );
}
