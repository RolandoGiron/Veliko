import type { NodeState } from "../api/types";

const MAP: Record<NodeState, string> = {
  sin_validar: "Sin validar",
  valido: "Válido",
  obsoleto: "Obsoleto",
};

export function FreshnessBadge({ state }: { state: NodeState }) {
  return (
    <span className={`badge badge--${state}`} title={MAP[state]}>
      <span className="dot" />
      {MAP[state]}
    </span>
  );
}
