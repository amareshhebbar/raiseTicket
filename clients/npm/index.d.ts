export interface Ticket {
  id: string;
  repo: string;
  priority: "blocking" | "high" | "normal" | "low";
  status: "pending" | "in_progress" | "done" | "failed";
  error_summary: string;
  raw_log_ref: string;
  command: string | null;
  test_id: string | null;
  created_at: string;
}

export declare class IssueLoop {
  constructor(options?: { baseUrl?: string });
  health(): Promise<{ status: string }>;
  getTopError(repo: string): Promise<Ticket | null>;
  getAllErrors(repo: string): Promise<Ticket[]>;
  resolve(ticketId: string): Promise<{ status: string }>;
  fail(ticketId: string): Promise<{ status: string }>;
}