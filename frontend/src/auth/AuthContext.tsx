import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api } from "../api/client";

interface AuthState { email: string | null; login: (e: string, p: string) => Promise<void>;
  register: (e: string, p: string) => Promise<void>; logout: () => void; }

const Ctx = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [email, setEmail] = useState<string | null>(null);
  useEffect(() => {
    if (localStorage.getItem("velvyko_token")) api.me().then((u) => setEmail(u.email)).catch(() => {});
  }, []);
  const login = async (e: string, p: string) => {
    const r = await api.login(e, p);
    localStorage.setItem("velvyko_token", r.access_token);
    const u = await api.me(); setEmail(u.email);
  };
  const register = async (e: string, p: string) => { await api.register(e, p); await login(e, p); };
  const logout = () => { localStorage.removeItem("velvyko_token"); setEmail(null); };
  return <Ctx.Provider value={{ email, login, register, logout }}>{children}</Ctx.Provider>;
}

export const useAuth = () => {
  const c = useContext(Ctx);
  if (!c) throw new Error("useAuth outside provider");
  return c;
};
