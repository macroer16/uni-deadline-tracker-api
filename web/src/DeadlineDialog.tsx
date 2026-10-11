import { FormEvent, useEffect, useRef, useState } from "react";
import { api } from "./api";
import { fromLocalInput, toLocalInput } from "./time";
import type { Deadline, Module, Status } from "./types";

interface Props {
  deadline: Deadline | null;
  modules: Module[];
  onClose: () => void;
  onSaved: () => void;
}

export function DeadlineDialog({ deadline, modules, onClose, onSaved }: Props) {
  const ref = useRef<HTMLDialogElement>(null);
  const [title, setTitle] = useState(deadline?.title ?? "");
  const [moduleId, setModuleId] = useState<string>(deadline?.module_id ? String(deadline.module_id) : "");
  const [due, setDue] = useState(deadline ? toLocalInput(deadline.due_at) : "");
  const [weight, setWeight] = useState(deadline?.weight_percent != null ? String(deadline.weight_percent) : "");
  const [status, setStatus] = useState<Status>(deadline?.status ?? "todo");
  const [notes, setNotes] = useState(deadline?.notes ?? "");
  const [error, setError] = useState("");

  // showModal gives focus trapping, Escape to close and a backdrop for free.
  useEffect(() => { ref.current?.showModal(); }, []);

  async function save(e: FormEvent) {
    e.preventDefault();
    const body = {
      title: title.trim(),
      module_id: moduleId ? Number(moduleId) : null,
      due_at: fromLocalInput(due),
      weight_percent: weight === "" ? null : Number(weight),
      status,
      notes: notes.trim() || null,
    };
    try {
      if (deadline) await api.updateDeadline(deadline.id, body);
      else await api.createDeadline(body);
      onSaved();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function remove() {
    if (!deadline || !confirm(`Delete “${deadline.title}”? This can't be undone.`)) return;
    try {
      await api.deleteDeadline(deadline.id);
      onSaved();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <dialog ref={ref} onClose={onClose} className="dialog" aria-labelledby="dialog-title">
      <form onSubmit={save}>
        <h2 id="dialog-title">{deadline ? "Edit deadline" : "Add deadline"}</h2>
        <label>
          What's due
          <input required maxLength={200} value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Coursework 1: report" autoFocus />
        </label>
        <div className="two">
          <label>
            Due
            <input type="datetime-local" required value={due} onChange={(e) => setDue(e.target.value)} />
          </label>
          <label>
            Worth (%)
            <input type="number" min={0} max={100} value={weight} onChange={(e) => setWeight(e.target.value)} />
          </label>
        </div>
        <div className="two">
          <label>
            Module
            <select value={moduleId} onChange={(e) => setModuleId(e.target.value)}>
              <option value="">None</option>
              {modules.map((m) => <option key={m.id} value={m.id}>{m.code} {m.name}</option>)}
            </select>
          </label>
          <label>
            Status
            <select value={status} onChange={(e) => setStatus(e.target.value as Status)}>
              <option value="todo">To do</option>
              <option value="in_progress">In progress</option>
              <option value="submitted">Submitted</option>
            </select>
          </label>
        </div>
        <label>
          Notes
          <textarea rows={3} maxLength={5000} value={notes} onChange={(e) => setNotes(e.target.value)} />
        </label>
        {error && <p className="error" role="alert">{error}</p>}
        <div className="dialog-actions">
          {deadline && <button type="button" className="danger" onClick={remove}>Delete</button>}
          <span className="spacer" />
          <button type="button" className="quiet" onClick={() => ref.current?.close()}>Cancel</button>
          <button className="primary">{deadline ? "Save changes" : "Add deadline"}</button>
        </div>
      </form>
    </dialog>
  );
}
