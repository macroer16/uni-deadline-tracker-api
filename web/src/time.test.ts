import { describe, expect, it } from "vitest";
import { countdown, groupDeadlines, nextUp, relative } from "./time";
import type { Deadline } from "./types";

const now = new Date("2026-11-02T12:00:00Z");
const d = (id: number, due_at: string, urgency: Deadline["urgency"]): Deadline => ({
  id, title: `D${id}`, module_id: null, module_code: null, due_at, weight_percent: null,
  status: urgency === "done" ? "submitted" : "todo", notes: null, urgency,
});

describe("countdown", () => {
  it("shows at most two units", () => {
    expect(countdown("2026-11-05T16:30:00Z", now)).toBe("3 days 4 hours");
    expect(countdown("2026-11-02T17:20:00Z", now)).toBe("5 hours 20 min");
    expect(countdown("2026-11-02T12:12:00Z", now)).toBe("12 min");
  });
  it("uses singular words", () => {
    expect(countdown("2026-11-03T13:00:00Z", now)).toBe("1 day 1 hour");
  });
  it("drops a zero second unit", () => {
    expect(countdown("2026-11-04T12:00:00Z", now)).toBe("2 days");
  });
  it("says now when the time has passed", () => {
    expect(countdown("2026-11-01T12:00:00Z", now)).toBe("now");
  });
});

describe("relative", () => {
  it("handles past and future", () => {
    expect(relative("2026-11-02T15:00:00Z", now)).toBe("in 3 hours");
    expect(relative("2026-10-31T12:00:00Z", now)).toBe("overdue by 2 days");
  });
});

describe("grouping", () => {
  const list = [
    d(1, "2026-11-20T09:00:00Z", "later"),
    d(2, "2026-11-03T09:00:00Z", "due_soon"),
    d(3, "2026-11-01T09:00:00Z", "overdue"),
    d(4, "2026-10-20T09:00:00Z", "done"),
    d(5, "2026-10-25T09:00:00Z", "done"),
    d(6, "2026-11-02T18:00:00Z", "due_soon"),
  ];
  it("groups by urgency, soonest first, newest submitted first", () => {
    const g = groupDeadlines(list);
    expect(g.due_soon.map((x) => x.id)).toEqual([6, 2]);
    expect(g.done.map((x) => x.id)).toEqual([5, 4]);
    expect(g.overdue.map((x) => x.id)).toEqual([3]);
  });
  it("next up skips overdue and submitted", () => {
    expect(nextUp(list)?.id).toBe(6);
    expect(nextUp([d(3, "2026-11-01T09:00:00Z", "overdue")])).toBeNull();
  });
});
