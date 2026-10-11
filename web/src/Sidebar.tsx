import { FormEvent, useState } from "react";
import { api } from "./api";
import type { Deadline, Module } from "./types";

interface Props {
  modules: Module[];
  deadlines: Deadline[];
  onChange: () => void;
  onError: (message: string) => void;
}

export function Sidebar({ modules, deadlines, onChange, onError }: Props) {
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [calendarUrl, setCalendarUrl] = useState("");
  const [copied, setCopied] = useState(false);

  async function addModule(e: FormEvent) {
    e.preventDefault();
    try {
      await api.createModule(code.trim(), name.trim());
      setCode("");
      setName("");
      onChange();
    } catch (err) {
      onError((err as Error).message);
    }
  }

  async function removeModule(m: Module) {
    if (!confirm(`Remove ${m.code}? Its deadlines are kept.`)) return;
    try {
      await api.deleteModule(m.id);
      onChange();
    } catch (err) {
      onError((err as Error).message);
    }
  }

  async function makeLink() {
    if (calendarUrl && !confirm("Make a new link? The old one will stop working.")) return;
    try {
      setCalendarUrl((await api.calendarLink()).url);
      setCopied(false);
    } catch (err) {
      onError((err as Error).message);
    }
  }

  const openCount = (id: number) => deadlines.filter((d) => d.module_id === id && d.status !== "submitted").length;

  return (
    <aside className="side">
      <section>
        <h2>Modules</h2>
        {modules.length === 0 && <p className="quiet-text">Add a module to group deadlines by it.</p>}
        <ul className="modules">
          {modules.map((m) => (
            <li key={m.id}>
              <span className="code">{m.code}</span>
              <span className="module-name">{m.name}</span>
              <span className="module-count" title="Not yet submitted">{openCount(m.id)}</span>
              <button className="icon" aria-label={`Remove ${m.code}`} onClick={() => removeModule(m)}>×</button>
            </li>
          ))}
        </ul>
        <form className="module-form" onSubmit={addModule}>
          <label className="visually-hidden" htmlFor="m-code">Module code</label>
          <input id="m-code" required maxLength={20} pattern="[A-Za-z0-9_\-]+" placeholder="Code" value={code} onChange={(e) => setCode(e.target.value)} />
          <label className="visually-hidden" htmlFor="m-name">Module name</label>
          <input id="m-name" required maxLength={120} placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} />
          <button className="quiet">Add</button>
        </form>
      </section>

      <section>
        <h2>Calendar</h2>
        <p className="quiet-text">Subscribe in Google, Outlook or Apple Calendar to see every deadline there, with a reminder the day before.</p>
        {calendarUrl ? (
          <>
            <input className="calendar-url" readOnly value={calendarUrl} onFocus={(e) => e.target.select()} aria-label="Your private calendar link" />
            <div className="calendar-actions">
              <button
                className="quiet"
                onClick={async () => {
                  try { await navigator.clipboard.writeText(calendarUrl); setCopied(true); } catch { /* clipboard blocked: the field is selectable */ }
                }}
              >
                {copied ? "Copied" : "Copy link"}
              </button>
              <button className="link" onClick={makeLink}>Make a new link</button>
            </div>
            <p className="quiet-text">Keep it private: anyone with the link can see your deadlines.</p>
          </>
        ) : (
          <button className="quiet" onClick={makeLink}>Get calendar link</button>
        )}
      </section>
    </aside>
  );
}
