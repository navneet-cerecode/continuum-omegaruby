import {
  useEffect,
  useRef,
  type ButtonHTMLAttributes,
  type ReactNode,
} from "react";
import { ArrowRight, FileText, LoaderCircle, X } from "lucide-react";

// The API includes different graph entity shapes; keep their properties intact.
export type RecordData = Record<string, any>;
export type View = "context" | "investigation" | "queue";
let csrfToken = "";
export function setApiSession(token = "") {
  csrfToken = token;
}

export async function api(
  path: string,
  body?: RecordData,
  method?: string,
  signal?: AbortSignal,
) {
  const response = await fetch("/api" + path, {
    method: method || (body ? "POST" : "GET"),
    headers: {
      "Content-Type": "application/json",
      ...(csrfToken ? { "X-CSRF-Token": csrfToken } : {}),
    },
    credentials: "same-origin",
    ...(body ? { body: JSON.stringify(body) } : {}),
    signal,
  });
  const data = await response.json();
  if (response.status === 401 && path !== "/auth/login")
    window.dispatchEvent(new Event("continuum-session-expired"));
  if (!response.ok)
    throw new Error(
      data.error ||
        (typeof data.detail === "string"
          ? data.detail
          : data.detail?.[0]?.msg) ||
        "The request could not be completed. Try again.",
    );
  return data;
}

export function Button({
  children,
  variant = "primary",
  loading,
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "text" | "danger";
  loading?: boolean;
}) {
  return (
    <button
      type="button"
      {...props}
      disabled={props.disabled || loading}
      className={`button ${variant} ${className}`}
    >
      {loading && (
        <LoaderCircle size={16} className="spin" aria-hidden="true" />
      )}
      {children}
    </button>
  );
}
export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "mint" | "amber" | "danger";
}) {
  return <span className={`badge ${tone}`}>{children}</span>;
}
export function Source({
  source,
  onInspect,
}: {
  source: RecordData;
  onInspect: (id: string) => void;
}) {
  return (
    <button
      type="button"
      className="source"
      onClick={() => onInspect(source.id)}
    >
      <span className="source-icon">
        <FileText size={17} aria-hidden="true" />
      </span>
      <span>
        {source.name || source.id}
        <small>
          {source.id} · v{source.version || 1}
        </small>
      </span>
      <ArrowRight size={15} aria-hidden="true" />
    </button>
  );
}
export function PathView({
  path,
  onInspect,
}: {
  path: string[];
  onInspect: (id: string) => void;
}) {
  return (
    <ol className="path-list" aria-label="Recorded dependency path">
      {path.map((id, index) => (
        <li key={`${id}-${index}`}>
          {index > 0 && <ArrowRight size={13} aria-label="depends on" />}
          <button onClick={() => onInspect(id)}>
            {id.replaceAll("-", " ")}
          </button>
        </li>
      ))}
    </ol>
  );
}
export function EmptyState({
  icon,
  title,
  children,
  action,
}: {
  icon: ReactNode;
  title: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="empty-state">
      <span className="empty-icon">{icon}</span>
      <h3>{title}</h3>
      <p>{children}</p>
      {action}
    </div>
  );
}
export function Modal({
  children,
  label,
  onClose,
  className = "",
}: {
  children: ReactNode;
  label: string;
  onClose: () => void;
  className?: string;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;
  useEffect(() => {
    const dialog = ref.current!;
    const trigger = document.activeElement as HTMLElement | null;
    const overflow = document.body.style.overflow;
    dialog.showModal();
    document.body.style.overflow = "hidden";
    return () => {
      dialog.close();
      document.body.style.overflow = overflow;
      if (trigger?.isConnected) trigger.focus();
    };
  }, []);
  return (
    <dialog
      ref={ref}
      aria-label={label}
      aria-modal="true"
      className={`modal ${className}`}
      onKeyDown={(event) => {
        if (event.key !== "Tab") return;
        const controls = Array.from(
          event.currentTarget.querySelectorAll<HTMLElement>(
            'button:not(:disabled), a[href], input:not(:disabled), textarea:not(:disabled), select:not(:disabled), summary, [tabindex="0"]',
          ),
        ).filter((element) => element.getClientRects().length > 0);
        const first = controls[0],
          last = controls[controls.length - 1];
        if (!first) {
          event.preventDefault();
          return;
        }
        if (
          event.shiftKey &&
          (document.activeElement === first ||
            document.activeElement === event.currentTarget)
        ) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }}
      onCancel={(event) => {
        event.preventDefault();
        closeRef.current();
      }}
      onClick={(event) => {
        const bounds = event.currentTarget.getBoundingClientRect();
        if (
          event.target === event.currentTarget &&
          (event.clientX < bounds.left ||
            event.clientX > bounds.right ||
            event.clientY < bounds.top ||
            event.clientY > bounds.bottom)
        )
          closeRef.current();
      }}
    >
      {children}
    </dialog>
  );
}
export function CloseButton({
  onClick,
  label = "Close",
}: {
  onClick: () => void;
  label?: string;
}) {
  return (
    <button
      type="button"
      className="icon-button"
      onClick={onClick}
      aria-label={label}
    >
      <X size={19} aria-hidden="true" />
    </button>
  );
}
export function initials(name: string) {
  return name
    .split(" ")
    .slice(0, 2)
    .map((part) => part[0])
    .join("");
}
