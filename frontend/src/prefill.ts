import type { AuditEvent } from "./types";

export interface PaymentPrefill {
  kind: "invoice" | "lease";
  ref_id: number;
  amount: number;
}

// The audit trail truncates tool results to stay readable (output/audit_trail.json,
// see backend/audit.py's _short()), so a get_invoice_status/get_lease_and_cash_status
// result can be cut off mid-JSON before it reaches the dashboard. The fields we need
// (invoice_id/amount, lease_id/monthly_rent) always appear near the start of those
// results, so a small regex pulls them out even when the tail is truncated — no need
// for the whole string to be valid JSON.
function field(text: string, key: string): number | null {
  const match = text.match(new RegExp(`"${key}"\\s*:\\s*(-?\\d+(?:\\.\\d+)?)`));
  return match ? Number(match[1]) : null;
}

export function prefillFromEvents(events: AuditEvent[]): PaymentPrefill | null {
  for (const e of events) {
    if (e.tool_name === "get_invoice_status") {
      const invoiceId = field(e.short_result, "invoice_id");
      const amount = field(e.short_result, "amount");
      if (invoiceId !== null && amount !== null) {
        return { kind: "invoice", ref_id: invoiceId, amount };
      }
    }
    if (e.tool_name === "get_lease_and_cash_status") {
      const leaseId = field(e.short_result, "lease_id");
      const rent = field(e.short_result, "monthly_rent");
      if (leaseId !== null && rent !== null) {
        return { kind: "lease", ref_id: leaseId, amount: rent };
      }
    }
  }
  return null;
}
