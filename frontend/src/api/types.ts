export type Tier = "free" | "pro" | "doctoral" | "university";
export type NodeState = "sin_validar" | "valido" | "obsoleto";
export type NodeType =
  | "problema" | "objetivos" | "hipotesis"
  | "variables" | "metodologia" | "instrumentos";

export interface NodeOut { type: NodeType; content: string; state: NodeState; }
export interface ProjectDetail { id: string; title: string; language: string; nodes: NodeOut[]; }
export interface ProjectSummary { id: string; title: string; language: string; }
export interface Issue {
  severity: "critica" | "mayor" | "menor";
  dimension: string; explanation: string; location: string | null;
}
export interface ValidationOut {
  status: string; score: number | null; issues: Issue[];
  suggestions: string[]; summary: string | null;
  mode: string | null; blocked: boolean; message: string | null;
  node_state: NodeState | null;
}
