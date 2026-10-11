export type Status = "todo" | "in_progress" | "submitted";
export type Urgency = "done" | "overdue" | "due_soon" | "this_week" | "later";

export interface Deadline {
  id: number;
  title: string;
  module_id: number | null;
  module_code: string | null;
  due_at: string;
  weight_percent: number | null;
  status: Status;
  notes: string | null;
  urgency: Urgency;
}

export interface Module {
  id: number;
  code: string;
  name: string;
}

export interface DeadlineInput {
  title: string;
  module_id: number | null;
  due_at: string;
  weight_percent: number | null;
  status: Status;
  notes: string | null;
}
