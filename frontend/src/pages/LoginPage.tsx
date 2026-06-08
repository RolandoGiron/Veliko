import { useState, type FormEvent } from "react";
import { useAuth } from "../auth/AuthContext";

export function LoginPage() {
  const { login, register } = useAuth();
  const [email, setEmail] = useState(""); const [pw, setPw] = useState("");
  const [mode, setMode] = useState<"login" | "register">("login");
  const [err, setErr] = useState<string | null>(null);
  const submit = async (e: FormEvent) => {
    e.preventDefault(); setErr(null);
    try { mode === "login" ? await login(email, pw) : await register(email, pw); }
    catch (x) { setErr(x instanceof Error ? x.message : String(x)); }
  };
  return (
    <form onSubmit={submit} style={{ maxWidth: 320, margin: "4rem auto", display: "grid", gap: 8 }}>
      <h1>Velvyko</h1>
      <input placeholder="email" value={email} onChange={(e) => setEmail(e.target.value)} />
      <input placeholder="contraseña" type="password" value={pw} onChange={(e) => setPw(e.target.value)} />
      {err && <p style={{ color: "crimson" }}>{err}</p>}
      <button type="submit">{mode === "login" ? "Entrar" : "Crear cuenta"}</button>
      <a onClick={() => setMode(mode === "login" ? "register" : "login")} style={{ cursor: "pointer" }}>
        {mode === "login" ? "Crear una cuenta" : "Ya tengo cuenta"}
      </a>
    </form>
  );
}
