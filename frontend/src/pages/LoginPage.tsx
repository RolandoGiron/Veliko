import { useState, type FormEvent } from "react";
import { useAuth } from "../auth/AuthContext";

const INDEX = [
  ["I", "Problema"],
  ["II", "Objetivos"],
  ["III", "Hipótesis"],
  ["IV", "Variables"],
  ["V", "Metodología"],
  ["VI", "Instrumentos"],
];

export function LoginPage() {
  const { login, register } = useAuth();
  const [email, setEmail] = useState("");
  const [pw, setPw] = useState("");
  const [mode, setMode] = useState<"login" | "register">("login");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setErr(null);
    setBusy(true);
    try {
      if (mode === "login") await login(email, pw);
      else await register(email, pw);
    } catch (x) {
      setErr(x instanceof Error ? x.message : String(x));
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="auth">
      {/* — Editorial left panel — */}
      <section className="auth__aside">
        <div className="rise" style={{ "--d": "60ms" } as React.CSSProperties}>
          <span className="brand">
            <span className="brand__mark">V</span>
            Velvyko
          </span>
        </div>

        <div>
          <p className="eyebrow rise" style={{ "--d": "160ms" } as React.CSSProperties}>
            Constructor de investigaciones
          </p>
          <h1 className="rise auth__headline" style={{ "--d": "240ms" } as React.CSSProperties}>
            Tu tesis,<br />
            <em>coherente</em> de raíz.
          </h1>
          <p className="lede rise" style={{ "--d": "330ms", maxWidth: "30ch" } as React.CSSProperties}>
            Construye nodo a nodo y deja que la validación de coherencia revise
            cada pieza antes de avanzar.
          </p>
        </div>

        <ol className="auth__index rise" style={{ "--d": "440ms" } as React.CSSProperties}>
          {INDEX.map(([num, label], i) => (
            <li key={label} style={{ "--d": `${500 + i * 60}ms` } as React.CSSProperties}>
              <span className="auth__num">{num}</span>
              {label}
            </li>
          ))}
        </ol>
      </section>

      {/* — Form card — */}
      <section className="auth__panel">
        <form
          className="card auth__card rise"
          onSubmit={submit}
          style={{ "--d": "200ms" } as React.CSSProperties}
        >
          <header className="auth__cardhead">
            <h2>{mode === "login" ? "Bienvenido de vuelta" : "Crea tu cuenta"}</h2>
            <p className="auth__cardsub">
              {mode === "login"
                ? "Entra para continuar tus investigaciones."
                : "Empieza a estructurar tu primera investigación."}
            </p>
          </header>

          <div className="stack" style={{ gap: "1.1rem" }}>
            <label>
              <span className="field-label">Correo</span>
              <input
                className="field"
                type="email"
                placeholder="tu@universidad.edu"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                required
              />
            </label>
            <label>
              <span className="field-label">Contraseña</span>
              <input
                className="field"
                type="password"
                placeholder="••••••••"
                value={pw}
                onChange={(e) => setPw(e.target.value)}
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                required
              />
            </label>

            {err && <p className="auth__err pop">{err}</p>}

            <button className="btn btn--primary btn--block" type="submit" disabled={busy}>
              {busy ? "Un momento…" : mode === "login" ? "Entrar" : "Crear cuenta"}
            </button>
          </div>

          <footer className="auth__cardfoot">
            {mode === "login" ? "¿Aún no tienes cuenta?" : "¿Ya tienes cuenta?"}{" "}
            <button
              type="button"
              className="linkbtn"
              onClick={() => {
                setErr(null);
                setMode(mode === "login" ? "register" : "login");
              }}
            >
              {mode === "login" ? "Crear una cuenta" : "Iniciar sesión"}
            </button>
          </footer>
        </form>
      </section>
    </main>
  );
}
