import type { NodeState } from "../api/types";

const MAP: Record<NodeState, { icon: string; label: string }> = {
  sin_validar: { icon: "⚪", label: "Sin validar" },
  valido: { icon: "🟢", label: "Válido" },
  obsoleto: { icon: "🟡", label: "Obsoleto" },
};

export function FreshnessBadge({ state }: { state: NodeState }) {
  const m = MAP[state];
  return <span title={m.label}>{m.icon} {m.label}</span>;
}
