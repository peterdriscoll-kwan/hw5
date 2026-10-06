import { useEffect, useRef, useState } from "react";
import type { ApprovePaymentResponse, AuditEvent, RunTicketResponse, TicketSummary } from "../types";
import { approvePayment, getEvents, runTicket } from "../api";
import { prefillFromEvents } from "../prefill";
import EventFeed from "./EventFeed";
import AgentSummaries from "./AgentSummaries";
import ApprovalSlip from "./ApprovalSlip";

interface Props {
  ticket: TicketSummary;
  onTicketChanged: () => void;
  onRunningChange: (ticketId: number | null) => void;
  onCashChanged: () => void;
}

export default function Desk({ ticket, onTicketChanged, onRunningChange, onCashChanged }: Props) {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [running, setRunning] = useState(false);
  const [lastRun, setLastRun] = useState<RunTicketResponse | null>(null);
  const [approveBusy, setApproveBusy] = useState(false);
  const [lastApproval, setLastApproval] = useState<ApprovePaymentResponse | null>(null);
  const pollRef = useRef<number | null>(null);

  // Switching tickets: load this ticket's own history, drop any other ticket's state.
  useEffect(() => {
    setLastRun(null);
    setLastApproval(null);
    getEvents(ticket.id).then((r) => setEvents(r.events));
  }, [ticket.id]);

  function stopPolling() {
    if (pollRef.current !== null) {
      window.clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }

  async function handleRun() {
    setRunning(true);
    onRunningChange(ticket.id);
    setLastRun(null);
    pollRef.current = window.setInterval(() => {
      getEvents(ticket.id).then((r) => setEvents(r.events)).catch(() => {});
    }, 1200);
    try {
      const result = await runTicket(ticket.id);
      setLastRun(result);
    } finally {
      stopPolling();
      const final = await getEvents(ticket.id);
      setEvents(final.events);
      setRunning(false);
      onRunningChange(null);
      onTicketChanged();
    }
  }

  useEffect(() => stopPolling, []);

  async function handleApprove(payload: {
    kind: "invoice" | "lease";
    ref_id: number;
    amount: number;
    account: string;
    approved_by: string;
  }) {
    setApproveBusy(true);
    try {
      const result = await approvePayment(payload);
      setLastApproval(result);
      if (result.paid) {
        onCashChanged();
      }
    } finally {
      setApproveBusy(false);
    }
  }

  const prefill = prefillFromEvents(events);
  const showApproval = ticket.status === "needs_approval" || lastRun?.requires_human_approval;

  return (
    <section className="desk">
      <header className="desk__header">
        <div>
          <span className="desk__eyebrow">Ticket #{ticket.id} — {ticket.type.replace("_", " ")}</span>
          <h1 className="desk__title">{ticket.subject}</h1>
          <p className="desk__requester">Requested by {ticket.requester}</p>
        </div>
        <button className="bell-button" onClick={handleRun} disabled={running}>
          <span className="bell-button__icon">🔔</span>
          {running ? "Working…" : "Ring for the Team"}
        </button>
      </header>

      {lastRun?.summary && (
        <div className="outcome-banner">
          <b>Outcome:</b> {lastRun.summary}
          {lastRun.delegations.length > 0 && (
            <span className="outcome-banner__chain"> — delegated to {lastRun.delegations.join(" → ")}</span>
          )}
        </div>
      )}

      <AgentSummaries events={events} bossSummary={lastRun?.summary ?? null} />

      <div className="desk__columns">
        <div className="ledger-pad">
          <h2 className="ledger-pad__title">What the team is doing</h2>
          <EventFeed events={events} />
        </div>

        {showApproval && (
          <div className="approval-column">
            {prefill ? (
              <>
                <h2 className="approval-column__title">Approve a Payment</h2>
                <p className="approval-column__hint">
                  {lastRun?.approval_reason ?? "This ticket is waiting on a human before any money moves."}
                </p>
                <ApprovalSlip
                  ticketId={ticket.id}
                  prefill={prefill}
                  onApprove={handleApprove}
                  lastResult={lastApproval}
                  busy={approveBusy}
                />
              </>
            ) : (
              <>
                <h2 className="approval-column__title">Human Decision Needed</h2>
                <p className="approval-column__hint">
                  {lastRun?.approval_reason ?? "This ticket needs a human call before it can move forward."}
                </p>
                <div className="decision-note">
                  No payment is being requested here — this is a policy call (like the price override above).
                  Review the team's recommendation in the cards above and act on it outside this board.
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
