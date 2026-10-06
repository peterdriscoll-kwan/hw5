// Mirrors backend/models.py — kept in one place so every component agrees on the shape.

export type TicketStatus = "open" | "in_progress" | "needs_approval" | "resolved";

export type AgentName = "boss" | "inventory" | "accounting" | "facilities" | "customer_service";

export interface TicketSummary {
  id: number;
  type: string;
  subject: string;
  requester: string;
  status: TicketStatus;
  is_resolved: boolean;
}

export interface PendingApproval {
  tool_name: string;
  args: string;
  tool_call_id: string;
}

export interface RunTicketResponse {
  ticket_id: number;
  status: TicketStatus;
  summary: string | null;
  requires_human_approval: boolean;
  approval_reason: string | null;
  delegations: AgentName[];
  pending_approvals: PendingApproval[];
}

export type StopReason = "ok" | "error" | "deferred_approval";

export interface AuditEvent {
  timestamp: string;
  ticket_id: number;
  agent: string;
  tool_name: string;
  short_args: string;
  short_result: string;
  stop_reason: StopReason;
}

export interface ApprovePaymentRequest {
  kind: "invoice" | "lease";
  ref_id: number;
  amount: number;
  account: string;
  approved_by: string;
}

export interface ApprovePaymentResponse {
  paid: boolean;
  message: string | null;
  payment_id: number | null;
  kind: string | null;
  ref_id: number | null;
  amount: number | null;
  account: string | null;
  approved_by: string | null;
  paid_at: string | null;
  new_cash_balance: number | null;
  invoice_marked_paid: boolean | null;
}

export interface CashBalance {
  found: boolean;
  account: string | null;
  balance: number | null;
  as_of: string | null;
  message: string | null;
}
