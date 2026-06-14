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

export type ExistenceStatus = "encontrada" | "no_encontrada" | "no_verificable";

export interface CandidateOut {
  title: string;
  doi: string | null;
  year: number | null;
  source: string;
}

export interface FindingOut {
  node_type: NodeType;
  raw: string;
  surname: string;
  year: string;
  narrative: boolean;
  format_issues: { severity: string; code: string; message: string }[];
  existence_status: ExistenceStatus;
  candidates: CandidateOut[];
}

export interface CitationRunOut {
  id: string;
  created_at: string;
  project_issues: { severity: string; code: string; message: string }[];
  llm_used: boolean;
  llm_summary: string | null;
  llm_issues: { severity: string; code: string; message: string; citation: string | null }[];
  llm_message: string | null;
  findings: FindingOut[];
}
