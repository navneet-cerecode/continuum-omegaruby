import { useEffect, useRef, useState } from "react";
import { ArrowRight, FileSearch, Search, LoaderCircle } from "lucide-react";
import {
  api,
  CloseButton,
  EmptyState,
  Modal,
  type RecordData,
  type View,
} from "./ui";

export function CommandSearch({
  onClose,
  onInspect,
  onNavigate,
}: {
  onClose: () => void;
  onInspect: (id: string) => void;
  onNavigate: (view: View) => void;
}) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<RecordData[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const list = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const controller = new AbortController();
    setResults([]);
    setError("");
    if (!query.trim()) {
      setLoading(false);
      return () => controller.abort();
    }
    setLoading(true);
    const timer = setTimeout(() => {
      api(
        "/search?q=" + encodeURIComponent(query.trim()),
        undefined,
        undefined,
        controller.signal,
      )
        .then(setResults)
        .catch((e: Error) => {
          if (e.name !== "AbortError") setError(e.message);
        })
        .finally(() => {
          if (!controller.signal.aborted) setLoading(false);
        });
    }, 180);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [query]);
  return (
    <Modal
      label="Search workspace"
      onClose={onClose}
      className="command-dialog"
    >
      <div className="command-input">
        <Search size={21} />
        <input
          autoFocus
          aria-label="Search all company context"
          placeholder="Search company context…"
          maxLength={100}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "ArrowDown") {
              e.preventDefault();
              list.current?.querySelector<HTMLButtonElement>("button")?.focus();
            }
            if (e.key === "Enter" && results.length) {
              onClose();
              onInspect(results[0].entity.id);
            }
          }}
        />
        {loading && <LoaderCircle className="spin" size={18} />}
        <CloseButton label="Close search" onClick={onClose} />
      </div>
      <div
        className="command-results"
        ref={list}
        onKeyDown={(e) => {
          if (!["ArrowDown", "ArrowUp"].includes(e.key)) return;
          const buttons = Array.from(
            list.current?.querySelectorAll<HTMLButtonElement>("button") || [],
          );
          const index = buttons.indexOf(
            document.activeElement as HTMLButtonElement,
          );
          if (index >= 0) {
            e.preventDefault();
            buttons[
              (index + (e.key === "ArrowDown" ? 1 : -1) + buttons.length) %
                buttons.length
            ]?.focus();
          }
        }}
      >
        <p className="section-label">
          {query.trim() ? "COMPANY GRAPH" : "JUMP TO"}
        </p>
        {!query.trim() ? (
          (
            [
              [
                "context",
                "Company context",
                "Readiness, projects, and evidence",
              ],
              [
                "investigation",
                "Change investigation",
                "Trace dependencies and current owners",
              ],
              [
                "queue",
                "Follow-up queue",
                "Review proposals and track approved work",
              ],
            ] as const
          ).map(([view, name, detail]) => (
            <button
              className="command-result"
              key={view}
              onClick={() => {
                onClose();
                onNavigate(view);
              }}
            >
              <span>
                <strong>{name}</strong>
                <small>{detail}</small>
              </span>
              <ArrowRight size={16} />
            </button>
          ))
        ) : error ? (
          <p role="alert" className="inline-error">
            {error}
          </p>
        ) : loading ? (
          <p role="status" className="search-status">
            Searching connected context…
          </p>
        ) : results.length ? (
          <>
            <p className="sr-only" role="status">
              {results.length} results
            </p>
            {results.map((result) => (
              <button
                className="command-result"
                key={result.entity.id}
                onClick={() => {
                  onClose();
                  onInspect(result.entity.id);
                }}
              >
                <span>
                  <strong>{result.entity.name}</strong>
                  <small>
                    {result.labels[0]} · {result.entity.id}
                  </small>
                </span>
                <ArrowRight size={16} />
              </button>
            ))}
          </>
        ) : (
          <EmptyState
            icon={<FileSearch size={24} />}
            title="No matching context"
          >
            Try a project name, a person, or a term like “security”.
          </EmptyState>
        )}
      </div>
      <div className="command-footer">
        <span>
          <kbd>↑</kbd>
          <kbd>↓</kbd> navigate <kbd>↵</kbd> open
        </span>
        <span>
          <kbd>esc</kbd> close
        </span>
      </div>
    </Modal>
  );
}
