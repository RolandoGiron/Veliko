import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export function AppBar() {
  const nav = useNavigate();
  const { email, logout } = useAuth();
  return (
    <header className="appbar">
      <div className="appbar__inner">
        <button
          className="brand"
          onClick={() => nav("/")}
          style={{ background: "none", border: 0, cursor: "pointer", padding: 0 }}
        >
          <span className="brand__mark">V</span>
          <span style={{ display: "grid", lineHeight: 1.1, textAlign: "left" }}>
            Velvyko
            <span className="brand__sub">Investigaciones</span>
          </span>
        </button>

        {email && (
          <div className="usermenu">
            <span className="who">{email}</span>
            <span aria-hidden>·</span>
            <button className="linkbtn" onClick={logout}>
              salir
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
