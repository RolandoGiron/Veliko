import type { ValidationOut } from "../api/types";

export function ValidationPanel({ result }: { result: ValidationOut | null }) {
  if (!result) return null;
  if (result.status !== "validated" && result.status !== "cached") {
    return <div style={{ background: "#fff7e6", padding: 12, borderRadius: 8 }}>
      ⚠️ {result.message ?? "No se pudo validar."}
    </div>;
  }
  return (
    <div style={{ border: "1px solid #ddd", padding: 12, borderRadius: 8 }}>
      <strong>Puntaje: {result.score}/100</strong>
      {result.mode === "estricto" && result.blocked &&
        <p style={{ color: "crimson" }}>🔒 Modo estricto: no puedes avanzar hasta mejorar este nodo.</p>}
      {result.summary && <p>{result.summary}</p>}
      {result.issues.length > 0 && (
        <ul>{result.issues.map((i, k) => (
          <li key={k}><b>[{i.severity}/{i.dimension}]</b> {i.explanation}</li>
        ))}</ul>
      )}
      {result.suggestions.length > 0 && (
        <><h4>Sugerencias</h4>
        <ul>{result.suggestions.map((s, k) => <li key={k}>{s}</li>)}</ul></>
      )}
    </div>
  );
}
