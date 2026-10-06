import type {
  ApprovePaymentRequest,
  ApprovePaymentResponse,
  AuditEvent,
  CashBalance,
  RunTicketResponse,
  TicketSummary,
} from "./types";

const BASE_URL = "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`${init?.method ?? "GET"} ${path} failed (${res.status}): ${detail}`);
  }
  return (await res.json()) as T;
}

export function getTickets(): Promise<{ tickets: TicketSummary[] }> {
  return request("/api/tickets");
}

export function runTicket(ticketId: number): Promise<RunTicketResponse> {
  return request(`/api/tickets/${ticketId}/run`, { method: "POST" });
}

export function getEvents(ticketId: number, limit = 100): Promise<{ events: AuditEvent[] }> {
  return request(`/api/events?ticket_id=${ticketId}&limit=${limit}`);
}

export function approvePayment(payload: ApprovePaymentRequest): Promise<ApprovePaymentResponse> {
  return request("/api/payments/approve", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getCashBalance(): Promise<CashBalance> {
  return request("/api/cash");
}

export function resetDatabase(): Promise<{ reset: boolean; message: string }> {
  return request("/api/reset", { method: "POST" });
}
