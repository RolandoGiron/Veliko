import { useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import type { ProjectDetail, ValidationOut } from "../api/types";
import { NodeEditor } from "../components/NodeEditor";

export function ProjectPage() {
  const { id = "" } = useParams(); const qc = useQueryClient();
  const { data } = useQuery<ProjectDetail>({
    queryKey: ["project", id], queryFn: () => api.project(id) as Promise<ProjectDetail>,
  });
  if (!data) return <p style={{ margin: "2rem" }}>Cargando…</p>;
  return (
    <div style={{ maxWidth: 760, margin: "2rem auto" }}>
      <h1>{data.title}</h1>
      {data.nodes.map((n) => (
        <NodeEditor key={n.type} node={n}
          onSave={async (c) => { await api.saveNode(id, n.type, c); qc.invalidateQueries({ queryKey: ["project", id] }); }}
          onValidate={async () => {
            const r = await api.validate(id, n.type) as ValidationOut;
            qc.invalidateQueries({ queryKey: ["project", id] });
            return r;
          }} />
      ))}
    </div>
  );
}
