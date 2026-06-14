import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import type { CitationRunOut, FindingOut, NodeType } from "../api/types";
import { NODE_META, NODE_ORDER } from "../ui/nodeMeta";

const EXISTENCE_UI: Record<string, { icon: string; label: string; tone: string }> = {
  encontrada: { icon: "🟢", label: "Encontrada en la literatura", tone: "good" },
  no_encontrada: { icon: "⚠", label: "Posible cita inventada", tone: "low" },
  no_verificable: { icon: "⚪", label: "No se pudo verificar", tone: "mid" },
};

function Finding({ f }: { f: FindingOut }) {
  const ex = EXISTENCE_UI[f.existence_status] ?? EXISTENCE_UI.no_verificable;
  return (
    <li className="cite" data-tone={ex.tone}>
      <div className="cite__head">
        <code className="cite__raw">{f.raw}</code>
        <span className="cite__existence" title={ex.label}>
          {ex.icon} {ex.label}
        </span>
      </div>
      {f.format_issues.length > 0 && (
        <ul className="cite__issues">
          {f.format_issues.map((it, k) => (
            <li key={k}>
              <span className={`chip chip--${it.severity}`}>{it.severity}</span>{" "}
              {it.message}
            </li>
          ))}
        </ul>
      )}
      {f.candidates.length > 0 && (
        <ul className="cite__candidates">
          {f.candidates.map((c, k) => (
            <li key={k}>
              {c.doi ? (
                <a href={c.doi.startsWith("http") ? c.doi : `https://doi.org/${c.doi}`}
                   target="_blank" rel="noreferrer">
                  {c.title || c.doi}
                </a>
              ) : (
                c.title
              )}{" "}
              <span className="muted">({c.source})</span>
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}

export function VerificationPanel({ projectId }: { projectId: string }) {
  const qc = useQueryClient();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { data: run } = useQuery<CitationRunOut>({
    queryKey: ["citations", projectId],
    queryFn: () => api.latestCitations(projectId) as Promise<CitationRunOut>,
    retry: false,
  });

  const onRun = async () => {
    setBusy(true);
    setError(null);
    try {
      const r = (await api.verifyCitations(projectId)) as CitationRunOut;
      qc.setQueryData(["citations", projectId], r);
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo verificar.");
    } finally {
      setBusy(false);
    }
  };

  const byNode = new Map<NodeType, FindingOut[]>();
  for (const f of run?.findings ?? []) {
    byNode.set(f.node_type, [...(byNode.get(f.node_type) ?? []), f]);
  }

  return (
    <section className="card verif">
      <header className="verif__head">
        <div>
          <h3>Verificación de citas</h3>
          <p className="node__hint">
            Formato APA-7 y existencia en Crossref/OpenAlex (anti-alucinación).
          </p>
        </div>
        <button className="btn" onClick={onRun} disabled={busy} aria-busy={busy}>
          {busy ? "Verificando…" : "Verificar citas"}
        </button>
      </header>

      {error && <p className="vp vp--warn" role="alert">⚠ {error}</p>}

      {run && (
        <div className="verif__body">
          {run.project_issues.map((i, k) => (
            <p key={k} className="muted">ℹ {i.message}</p>
          ))}

          {NODE_ORDER.filter((nt) => byNode.has(nt)).map((nt) => (
            <div key={nt} className="verif__group">
              <p className="field-label">{NODE_META[nt].label}</p>
              <ul className="verif__list">
                {byNode.get(nt)!.map((f, k) => <Finding key={k} f={f} />)}
              </ul>
            </div>
          ))}

          {run.llm_message && <p className="muted">ℹ {run.llm_message}</p>}
          {run.llm_used && (
            <div className="verif__llm">
              <p className="field-label">Revisión de estilo (IA)</p>
              {run.llm_summary && <p>{run.llm_summary}</p>}
              {run.llm_issues.length > 0 && (
                <ul className="cite__issues">
                  {run.llm_issues.map((it, k) => (
                    <li key={k}>
                      <span className={`chip chip--${it.severity}`}>{it.severity}</span>{" "}
                      {it.message} {it.citation && <code>{it.citation}</code>}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
