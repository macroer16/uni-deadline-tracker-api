// Small wrapper around fetch. Every request goes to /api, which the ingress (or the
// Vite dev server) forwards to FastAPI.
import type { Deadline, DeadlineInput, Module } from "./types";

const TOKEN_KEY = "due.token";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export const session = {
  get: (): string | null => {
    try { return localStorage.getItem(TOKEN_KEY); } catch { return null; }
  },
  set: (token: string) => {
    try { localStorage.setItem(TOKEN_KEY, token); } catch { /* private mode: stay signed in for this tab only */ }
  },
  clear: () => {
    try { localStorage.removeItem(TOKEN_KEY); } catch { /* nothing to clear */ }
  },
};

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const token = session.get();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && typeof init.body === "string") headers.set("Content-Type", "application/json");

  const res = await fetch(`/api${path}`, { ...init, headers });
  if (res.status === 401 && token) {
    session.clear();
    window.dispatchEvent(new Event("due:signed-out"));
  }
  if (!res.ok) {
    let message = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      // FastAPI sends either {"detail": "text"} or {"detail": [{msg: ...}]} for validation errors.
      if (typeof body.detail === "string") message = body.detail;
      else if (Array.isArray(body.detail)) message = body.detail.map((e: { msg: string }) => e.msg).join(". ");
    } catch { /* not JSON */ }
    throw new ApiError(res.status, message);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

export const api = {
  register: (email: string, password: string) =>
    request("/auth/register", { method: "POST", body: JSON.stringify({ email, password }) }),

  login: async (email: string, password: string) => {
    const form = new URLSearchParams({ username: email, password });
    const { access_token } = await request<{ access_token: string }>("/auth/login", { method: "POST", body: form });
    session.set(access_token);
  },

  me: () => request<{ email: string }>("/me"),
  deadlines: () => request<Deadline[]>("/deadlines"),
  createDeadline: (d: DeadlineInput) => request<Deadline>("/deadlines", { method: "POST", body: JSON.stringify(d) }),
  updateDeadline: (id: number, d: Partial<DeadlineInput>) =>
    request<Deadline>(`/deadlines/${id}`, { method: "PATCH", body: JSON.stringify(d) }),
  deleteDeadline: (id: number) => request<void>(`/deadlines/${id}`, { method: "DELETE" }),
  modules: () => request<Module[]>("/modules"),
  createModule: (code: string, name: string) =>
    request<Module>("/modules", { method: "POST", body: JSON.stringify({ code, name }) }),
  deleteModule: (id: number) => request<void>(`/modules/${id}`, { method: "DELETE" }),
  calendarLink: () => request<{ url: string }>("/me/calendar-link", { method: "POST" }),
};
