// Pure helpers for dates and grouping. Tested in time.test.ts.
import type { Deadline, Urgency } from "./types";

export const GROUPS: { key: Urgency; title: string }[] = [
  { key: "overdue", title: "Overdue" },
  { key: "due_soon", title: "Next 48 hours" },
  { key: "this_week", title: "This week" },
  { key: "later", title: "Later" },
  { key: "done", title: "Submitted" },
];

export function groupDeadlines(deadlines: Deadline[]): Record<Urgency, Deadline[]> {
  const groups: Record<Urgency, Deadline[]> = { overdue: [], due_soon: [], this_week: [], later: [], done: [] };
  for (const d of deadlines) groups[d.urgency].push(d);
  for (const list of Object.values(groups)) {
    list.sort((a, b) => a.due_at.localeCompare(b.due_at));
  }
  // Most recently submitted first: that's what you're likely to look back at.
  groups.done.reverse();
  return groups;
}

/** The deadline to show in the big countdown: soonest one not yet submitted and not overdue. */
export function nextUp(deadlines: Deadline[]): Deadline | null {
  const open = deadlines.filter((d) => d.urgency !== "done" && d.urgency !== "overdue");
  open.sort((a, b) => a.due_at.localeCompare(b.due_at));
  return open[0] ?? null;
}

/** "3 days 4 hours", "5 hours 20 min", "12 min". Never shows more than two units. */
export function countdown(dueIso: string, now: Date): string {
  let mins = Math.floor((new Date(dueIso).getTime() - now.getTime()) / 60000);
  if (mins <= 0) return "now";
  const days = Math.floor(mins / 1440);
  mins -= days * 1440;
  const hours = Math.floor(mins / 60);
  mins -= hours * 60;
  const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? "" : "s"}`;
  if (days > 0) return hours ? `${plural(days, "day")} ${plural(hours, "hour")}` : plural(days, "day");
  if (hours > 0) return mins ? `${plural(hours, "hour")} ${mins} min` : plural(hours, "hour");
  return `${mins} min`;
}

/** "Fri 4 Dec, 16:00" in the viewer's own time zone. */
export function formatDue(dueIso: string): string {
  const d = new Date(dueIso);
  const date = d.toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short" });
  const time = d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
  return `${date}, ${time}`;
}

/** "overdue by 2 days", "in 5 hours", for the line under each title. */
export function relative(dueIso: string, now: Date): string {
  const due = new Date(dueIso).getTime();
  if (due < now.getTime()) return `overdue by ${countdown(new Date(now.getTime() * 2 - due).toISOString(), now)}`;
  return `in ${countdown(dueIso, now)}`;
}

/** Value for <input type="datetime-local"> from an ISO string, in local time. */
export function toLocalInput(iso: string): string {
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/** The API rejects times without a timezone, so local input is converted to a full ISO string. */
export function fromLocalInput(value: string): string {
  return new Date(value).toISOString();
}
