export interface TimelineItem {
  id: string;
  type: string;
  title: string;
  description: string | null;
  user_id: string | null;
  user_name: string | null;
  created_at: string;
  payload: Record<string, unknown>;
}

export interface ApprovalTimelineProcess {
  id: string;
  status: string;
  started_at: string;
  finished_at: string | null;
}

export interface ApprovalTimelineTask {
  id: string;
  approver_id: string;
  approver_name: string | null;
  status: string;
  created_at: string;
  completed_at: string | null;
  comment: string | null;
}

export interface ApprovalTimelineStep {
  step_order: number;
  step_name: string;
  status: string;
  tasks: ApprovalTimelineTask[];
}

export interface ApprovalTimeline {
  process: ApprovalTimelineProcess | null;
  steps: ApprovalTimelineStep[];
}
