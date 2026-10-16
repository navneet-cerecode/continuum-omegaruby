import { useState } from "react";
import {
  ArrowRight,
  GitBranch,
  Layers3,
  ShieldCheck,
  Users,
} from "lucide-react";
type ImpactItem = {
  id: string;
  name: string;
  path: string[];
  edges: { source?: string }[];
};
const nodeNames: Record<string, string> = {
  "commitment-acme": "Acme commitment",
  "commitment-harbor": "Harbor commitment",
  "milestone-atlas": "Atlas availability",
  "decision-atlas": "Atlas launch decision",
  "milestone-export": "Export release gate",
  "decision-export": "Export release decision",
  "approval-export": "Security approval",
  "project-atlas": "Project Atlas",
};
export function FocusedGraph({
  items,
  onInspect,
  historical = false,
}: {
  items: ImpactItem[];
  onInspect: (id: string) => void;
  historical?: boolean;
}) {
  const [choice, setChoice] = useState("commitment-acme");
  const selected = items.find((item) => item.id === choice) || items[0];
  if (!selected) return null;
  return (
    <div className="focused-graph">
      <div className="graph-heading">
        <div>
          <span className="section-label">
            <GitBranch size={13} />{" "}
            {historical ? "HISTORICAL DEPENDENCY PATH" : "LIVE DEPENDENCY PATH"}
          </span>
          <h3>Follow the connection.</h3>
          <p>Every node and connection opens its recorded evidence.</p>
        </div>
        <label>
          Trace from
          <select
            aria-label="Focused dependency path"
            value={selected.id}
            onChange={(e) => setChoice(e.target.value)}
          >
            {items.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div
        className="graph-scroll"
        tabIndex={0}
        role="region"
        aria-label={`Dependency graph for ${selected.name}. Scroll to explore the full path.`}
      >
        <ol
          className="dependency-graph"
          aria-label={`Dependency path for ${selected.name}`}
        >
          {selected.path.map((id, index) => {
            const Icon = id.startsWith("approval")
              ? ShieldCheck
              : id.startsWith("commitment")
                ? Users
                : id.startsWith("decision")
                  ? GitBranch
                  : Layers3;
            const kind = id.split("-")[0];
            return (
              <li key={id}>
                <button
                  className={`graph-node ${index === selected.path.length - 1 ? "graph-prerequisite" : ""}`}
                  data-entity-id={id}
                  onClick={() => onInspect(id)}
                >
                  <span className="graph-node-top" aria-hidden="true">
                    <Icon size={18} />
                    <small>{String(index + 1).padStart(2, "0")}</small>
                  </span>
                  <small className="graph-kind" aria-hidden="true">
                    {kind}
                  </small>
                  <strong>
                    {id.startsWith("approval-export-restored-")
                      ? "Replacement security approval"
                      : id.startsWith("approval-restored-")
                        ? "Replacement approval"
                        : nodeNames[id] || id.replaceAll("-", " ")}
                  </strong>
                </button>
                {index < selected.path.length - 1 && (
                  <button
                    className="graph-edge"
                    disabled={!selected.edges[index]?.source}
                    aria-label={`Inspect dependency evidence: ${id} depends on ${selected.path[index + 1]}`}
                    title={
                      selected.edges[index]?.source
                        ? "Inspect connection evidence"
                        : "No edge evidence recorded"
                    }
                    onClick={() => {
                      const source = selected.edges[index]?.source;
                      if (source) onInspect(source);
                    }}
                  >
                    <span />
                    <ArrowRight size={16} />
                  </button>
                )}
              </li>
            );
          })}
        </ol>
      </div>
      <div className="graph-legend">
        <span>
          <span className="legend-dot" /> Recorded dependency
        </span>
        <span>
          <span className="legend-dot amber" /> Changed prerequisite
        </span>
        <strong>{selected.path.length - 1} hops</strong>
      </div>
      <p className="graph-explanation">
        Arrows mean “depends on”. A changed prerequisite flags the items that
        depend on it for review.
      </p>
    </div>
  );
}
