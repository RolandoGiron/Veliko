import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import type { ProjectDetail, ValidationOut, NodeType } from "../api/types";
import { NodeEditor } from "../components/NodeEditor";
import { AppBar } from "../components/AppBar";
import { NODE_ORDER } from "../ui/nodeMeta";

export function ProjectPage() {
  const { id = "" } = useParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const { data } = useQuery<ProjectDetail>({
    queryKey: ["project", id],
    queryFn: () => api.project(id) as Promise<ProjectDetail>,
  });

  if (!data) {
    return (
      <>
        <AppBar />
        <p className="muted-line container">Cargando…</p>
      </>
    );
  }

  const ordered = [...data.nodes].sort(
    (a, b) => NODE_ORDER.indexOf(a.type) - NODE_ORDER.indexOf(b.type)
  );
  const validated = data.nodes.filter((n) => n.state === "valido").length;

  return (
    <>
      <AppBar />
      <main className="container" style={{ padding: "2.5rem 1.5rem 6rem" }}>
        <button className="linkbtn back rise" onClick={() => nav("/")}>
          ← Mis investigaciones
        </button>

        <header className="proj-head rise" style={{ "--d": "60ms" } as React.CSSProperties}>
          <p className="eyebrow">Investigación</p>
          <h1>{data.title}</h1>
          <div className="progress">
            <span className="progress__count">
              {validated}/{data.nodes.length}
            </span>
            <span className="progress__track">
              <span
                className="progress__fill"
                style={{ width: `${(validated / data.nodes.length) * 100}%` }}
              />
            </span>
            <span className="progress__label">nodos válidos</span>
          </div>
        </header>

        <div className="spine">
          {ordered.map((n, i) => (
            <NodeEditor
              key={n.type}
              index={i}
              type={n.type as NodeType}
              node={n}
              last={i === ordered.length - 1}
              onSave={async (c) => {
                await api.saveNode(id, n.type, c);
                qc.invalidateQueries({ queryKey: ["project", id] });
              }}
              onValidate={async () => {
                const r = (await api.validate(id, n.type)) as ValidationOut;
                qc.invalidateQueries({ queryKey: ["project", id] });
                return r;
              }}
            />
          ))}
        </div>
      </main>
    </>
  );
}
