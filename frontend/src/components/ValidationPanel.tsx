import type { ValidationOut } from "../api/types";

export function ValidationPanel({ result }: { result: ValidationOut | null }) {
  if (!result) return null;

  if (result.status !== "validated" && result.status !== "cached") {
    return (
      <div className="vp vp--warn pop">
        <span className="vp__icon">⚠</span>
        <p>{result.message ?? "No se pudo validar."}</p>
      </div>
    );
  }

  const score = result.score ?? 0;
  const tone = score >= 80 ? "good" : score >= 55 ? "mid" : "low";

  return (
    <div className="vp pop">
      <div className="vp__score" data-tone={tone}>
        <span className="vp__num">{score}</span>
        <span className="vp__den">/100</span>
        <span className="vp__scorelabel">Coherencia</span>
      </div>

      <div className="vp__body">
        {result.mode === "estricto" && result.blocked && (
          <p className="vp__blocked">
            🔒 Modo estricto — no puedes avanzar hasta mejorar este nodo.
          </p>
        )}

        {result.summary && <p className="vp__summary">{result.summary}</p>}

        {result.issues.length > 0 && (
          <ul className="vp__issues">
            {result.issues.map((it, k) => (
              <li key={k}>
                <span className={`chip chip--${it.severity}`}>{it.severity}</span>
                <span className="vp__issuetext">
                  <strong>{it.dimension}</strong> — {it.explanation}
                </span>
              </li>
            ))}
          </ul>
        )}

        {result.suggestions.length > 0 && (
          <div className="vp__suggest">
            <p className="field-label">Sugerencias</p>
            <ul>
              {result.suggestions.map((s, k) => (
                <li key={k}>{s}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
