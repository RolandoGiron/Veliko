const BASE = "/api";

function token(): string | null { return localStorage.getItem("velvyko_token"); }

async function req<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json", ...(opts.headers as Record<string, string>) };
  const t = token();
  if (t) headers["Authorization"] = `Bearer ${t}`;
  const res = await fetch(`${BASE}${path}`, { ...opts, headers });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail ?? res.statusText);
  return res.json() as Promise<T>;
}

export const api = {
  register: (email: string, password: string) =>
    req("/auth/register", { method: "POST", body: JSON.stringify({ email, password }) }),
  login: (email: string, password: string) =>
    req<{ access_token: string }>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  me: () => req<{ id: string; email: string; tier: string }>("/auth/me"),
  projects: () => req("/projects"),
  createProject: (title: string) =>
    req("/projects", { method: "POST", body: JSON.stringify({ title }) }),
  project: (id: string) => req(`/projects/${id}`),
  saveNode: (pid: string, type: string, content: string) =>
    req(`/projects/${pid}/nodes/${type}`, { method: "PUT", body: JSON.stringify({ content }) }),
  validate: (pid: string, type: string) =>
    req(`/projects/${pid}/nodes/${type}/validate`, { method: "POST" }),
};
