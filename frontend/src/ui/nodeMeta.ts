import type { NodeType } from "../api/types";

export interface NodeMeta {
  roman: string;
  label: string;
  hint: string;
}

/** Canonical order + editorial labels for the six research nodes. */
export const NODE_META: Record<NodeType, NodeMeta> = {
  problema: { roman: "I", label: "Problema", hint: "El vacío o la pregunta que motiva el estudio." },
  objetivos: { roman: "II", label: "Objetivos", hint: "Lo que la investigación se propone lograr." },
  hipotesis: { roman: "III", label: "Hipótesis", hint: "La respuesta tentativa que pondrás a prueba." },
  variables: { roman: "IV", label: "Variables", hint: "Lo que se mide y cómo se relaciona." },
  metodologia: { roman: "V", label: "Metodología", hint: "El diseño y la ruta para obtener evidencia." },
  instrumentos: { roman: "VI", label: "Instrumentos", hint: "Las herramientas para recoger los datos." },
};

export const NODE_ORDER: NodeType[] = [
  "problema",
  "objetivos",
  "hipotesis",
  "variables",
  "metodologia",
  "instrumentos",
];
