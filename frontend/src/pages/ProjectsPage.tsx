import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import { AppBar } from "../components/AppBar";
import type { ProjectSummary } from "../api/types";

export function ProjectsPage() {
  const nav = useNavigate();
  const qc = useQueryClient();
  const [title, setTitle] = useState("");

  const { data: projects = [], isLoading } = useQuery<ProjectSummary[]>({
    queryKey: ["projects"],
    queryFn: () => api.projects() as Promise<ProjectSummary[]>,
  });

  const create = useMutation({
    mutationFn: () => api.createProject(title) as Promise<ProjectSummary>,
    onSuccess: (p) => {
      qc.invalidateQueries({ queryKey: ["projects"] });
      nav(`/projects/${p.id}`);
    },
  });

  return (
    <>
      <AppBar />
      <main className="container container--wide" style={{ padding: "3rem 1.5rem 5rem" }}>
        <section className="rise" style={{ "--d": "40ms" } as React.CSSProperties}>
          <p className="eyebrow">Tu mesa de trabajo</p>
          <h1 style={{ margin: "0.5rem 0 0.9rem" }}>Mis investigaciones</h1>
          <hr className="rule" />
        </section>

        {/* — Create — */}
        <form
          className="card rise creator"
          onSubmit={(e) => {
            e.preventDefault();
            if (title.trim()) create.mutate();
          }}
          style={{ "--d": "130ms" } as React.CSSProperties}
        >
          <input
            className="field"
            placeholder="Título de una nueva investigación…"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
          <button
            className="btn btn--primary"
            type="submit"
            disabled={!title.trim() || create.isPending}
          >
            {create.isPending ? "Creando…" : "Crear"}
          </button>
        </form>

        {/* — List — */}
        {isLoading ? (
          <p className="muted-line">Cargando investigaciones…</p>
        ) : projects.length === 0 ? (
          <div className="empty rise" style={{ "--d": "220ms" } as React.CSSProperties}>
            <span className="empty__mark">✦</span>
            <h3>Aún no hay nada aquí</h3>
            <p>Crea tu primera investigación arriba para empezar a construir.</p>
          </div>
        ) : (
          <ul className="proj-list">
            {projects.map((p, i) => (
              <li
                key={p.id}
                className="proj rise"
                style={{ "--d": `${220 + i * 70}ms` } as React.CSSProperties}
                onClick={() => nav(`/projects/${p.id}`)}
              >
                <span className="proj__index">{String(i + 1).padStart(2, "0")}</span>
                <span className="proj__body">
                  <span className="proj__title">{p.title}</span>
                  <span className="proj__meta">{p.language?.toUpperCase() || "ES"}</span>
                </span>
                <span className="proj__arrow" aria-hidden>
                  →
                </span>
              </li>
            ))}
          </ul>
        )}
      </main>
    </>
  );
}
