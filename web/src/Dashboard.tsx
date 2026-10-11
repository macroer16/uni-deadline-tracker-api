import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import { DeadlineDialog } from "./DeadlineDialog";
import { Sidebar } from "./Sidebar";
import { GROUPS, countdown, formatDue, groupDeadlines, nextUp, relative } from "./time";
import type { Deadline, Module, Status } from "./types";

const STATUS_LABEL: Record<Status, string> = { todo: "To do", in_progress: "In progress", submitted: "Submitted" };

function useNow(intervalMs = 30_000) {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), intervalMs);
    return () => clearInterval(t);
  }, [intervalMs]);
  return now;
}

export function Dashboard({ onSignOut }: { onSignOut: () => void }) {
  const now = useNow();
  const [email, setEmail] = useState("");
  const [deadlines, setDeadlines] = useState<Deadline[] | null>(null);
  const [modules, setModules] = useState<Module[]>([]);
  const [error, setError] = useState("");
  const [editing, setEditing] = useState<Deadline | "new" | null>(null);
  const [showDone, setShowDone] = useState(false);

  const reload = useCallback(async () => {
    try {
      const [d, m] = await Promise.all([api.deadlines(), api.modules()]);
      setDeadlines(d);
      setModules(m);
      setError("");
    } catch (err) {
      setError((err as Error).message);
    }
  }, []);

  useEffect(() => {
    reload();
    api.me().then((u) => setEmail(u.email)).catch(() => {});
  }, [reload]);

  async function setStatus(d: Deadline, status: Status) {
    try {
      await api.updateDeadline(d.id, { status });
      await reload();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  const groups = deadlines ? groupDeadlines(deadlines) : null;
  const next = deadlines ? nextUp(deadlines) : null;

  return (
    <div className="shell">
      <header className="topbar">
        <span className="wordmark small"><span className="mark">Due</span></span>
        <div className="account">
          <span className="email">{email}</span>
          <button className="link" onClick={onSignOut}>Sign out</button>
        </div>
      </header>

      <div className="layout">
        <main>
          <section className="next" aria-live="polite">
            {next ? (
              <>
                <p className="next-label">Next up{next.module_code ? `, ${next.module_code}` : ""}</p>
                <h1 className="next-title">{next.title}</h1>
                <p className="next-countdown"><span className="mark">{countdown(next.due_at, now)}</span></p>
                <p className="next-when">
                  <span>{formatDue(next.due_at)}</span>
                  {next.weight_percent != null && <span>Worth {next.weight_percent}% of the module</span>}
                </p>
              </>
            ) : deadlines ? (
              <>
                <h1 className="next-title">Nothing due.</h1>
                <p className="next-when">Add your first deadline and it will count down here.</p>
              </>
            ) : (
              <p className="next-when">Loading your deadlines…</p>
            )}
            <button className="primary" onClick={() => setEditing("new")}>Add deadline</button>
          </section>

          {error && <p className="error" role="alert">{error}</p>}

          {groups && GROUPS.map(({ key, title }) => {
            const list = groups[key];
            if (list.length === 0) return null;
            if (key === "done" && !showDone) {
              return (
                <button key={key} className="link show-done" onClick={() => setShowDone(true)}>
                  Show {list.length} submitted
                </button>
              );
            }
            return (
              <section key={key} className={`group group-${key}`}>
                <h2>{title} <span className="count">{list.length}</span></h2>
                <ul>
                  {list.map((d) => (
                    <li key={d.id} className="row">
                      <div className="row-main">
                        <button className="row-title" onClick={() => setEditing(d)}>
                          {d.module_code && <span className="code">{d.module_code}</span>}
                          <span className={key === "due_soon" ? "mark" : undefined}>{d.title}</span>
                        </button>
                        <span className="row-when">
                          <span>{formatDue(d.due_at)}</span>
                          {key !== "done" && <span className="rel">{relative(d.due_at, now)}</span>}
                          {d.weight_percent != null && <span>{d.weight_percent}% of the module</span>}
                        </span>
                      </div>
                      <label className="visually-hidden" htmlFor={`status-${d.id}`}>Status of {d.title}</label>
                      <select id={`status-${d.id}`} value={d.status} onChange={(e) => setStatus(d, e.target.value as Status)}>
                        {(Object.keys(STATUS_LABEL) as Status[]).map((s) => (
                          <option key={s} value={s}>{STATUS_LABEL[s]}</option>
                        ))}
                      </select>
                    </li>
                  ))}
                </ul>
              </section>
            );
          })}
        </main>

        <Sidebar modules={modules} deadlines={deadlines ?? []} onChange={reload} onError={setError} />
      </div>

      {editing && (
        <DeadlineDialog
          deadline={editing === "new" ? null : editing}
          modules={modules}
          onClose={() => setEditing(null)}
          onSaved={async () => { setEditing(null); await reload(); }}
        />
      )}
    </div>
  );
}
