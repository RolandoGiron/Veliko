import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import type { ProjectSummary } from "../api/types";

export function ProjectsPage() {
  const nav = useNavigate(); const qc = useQueryClient(); const { email, logout } = useAuth();
  const [title, setTitle] = useState("");
  const { data: projects = [] } = useQuery<ProjectSummary[]>({
    queryKey: ["projects"], queryFn: () => api.projects() as Promise<ProjectSummary[]>,
  });
  const create = useMutation({
    mutationFn: () => api.createProject(title) as Promise<ProjectSummary>,
    onSuccess: (p) => { qc.invalidateQueries({ queryKey: ["projects"] }); nav(`/projects/${p.id}`); },
  });
  return (
    <div style={{ maxWidth: 700, margin: "2rem auto" }}>
      <header style={{ display: "flex", justifyContent: "space-between" }}>
        <h1>Mis investigaciones</h1>
        <span>{email} · <a onClick={logout} style={{ cursor: "pointer" }}>salir</a></span>
      </header>
      <div style={{ display: "flex", gap: 8, margin: "1rem 0" }}>
        <input placeholder="Título de la investigación" value={title}
               onChange={(e) => setTitle(e.target.value)} style={{ flex: 1 }} />
        <button disabled={!title.trim()} onClick={() => create.mutate()}>Crear</button>
      </div>
      <ul>
        {projects.map((p) => (
          <li key={p.id}><a onClick={() => nav(`/projects/${p.id}`)} style={{ cursor: "pointer" }}>{p.title}</a></li>
        ))}
      </ul>
    </div>
  );
}
