"""Shared data types for the Campus Customs agent team.

Keeping these in one place means every agent (and the orchestrator that
runs them) agrees on the exact same shape for a reply, for delegation
context, and for an audit row — no agent invents its own ad hoc format.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field

TicketStatus = Literal["open", "in_progress", "needs_approval", "resolved"]

AgentName = Literal["boss", "inventory", "accounting", "facilities", "customer_service"]


class AgentReply(BaseModel):
    """The structured result every specialist agent produces for a ticket.

    This is the one output shape shared by all five agents so the Boss
    (and the orchestrator, and eventually the dashboard) can read any
    agent's result the same way, regardless of which agent produced it.
    """

    ticket_id: int = Field(description="The ticket this reply is about.")
    summary: str = Field(description="Plain-language account of what was found and/or done.")
    recommended_status: TicketStatus = Field(
        description="What the ticket's status should become. Use 'needs_approval' for anything "
        "a human must sign off on — a payment, a price override — rather than 'resolved'."
    )
    requires_human_approval: bool = Field(
        description="True if a human must review this before anything further happens "
        "(a payment, a discount, anything touching real money or a real customer commitment)."
    )
    approval_reason: str | None = Field(
        default=None, description="Why human approval is needed, if requires_human_approval is True."
    )
    delegations: list[str] = Field(
        default_factory=list,
        description="Which other agents (by name) this agent delegated to while working the ticket, in order.",
    )


@dataclass
class TicketContext:
    """Deps passed into every agent run for one ticket resolution.

    `chain` is the list of agents that have already touched this ticket
    in this resolution attempt (oldest first). Every delegation appends
    the delegating agent's name before handing off, and the delegate
    tool refuses once `chain` reaches `max_chain_length` — this is what
    stops two agents from bouncing a ticket back and forth forever.
    """

    ticket_id: int
    chain: list[AgentName] = field(default_factory=list)
    max_chain_length: int = 4


class AuditEntry(BaseModel):
    """One row of the append-only output/audit_trail.json audit log.

    Captures enough to reconstruct what happened without needing to
    re-run anything: which agent, which tool, what it was asked, what it
    got back, and why the run stopped. `short_args`/`short_result` are
    deliberately truncated — this is an audit trail, not a full replay
    log, so it stays readable and doesn't balloon with large payloads.
    """

    timestamp: str
    ticket_id: int
    agent: str
    tool_name: str
    short_args: str
    short_result: str
    stop_reason: Literal["ok", "error", "deferred_approval"]


class TicketSummary(BaseModel):
    """One row of the board's ticket list — just enough for an overview, not the full record."""

    id: int
    type: str
    subject: str
    requester: str
    status: TicketStatus
    is_resolved: bool


class TicketsResponse(BaseModel):
    tickets: list[TicketSummary]


class PendingApproval(BaseModel):
    """One tool call an agent attempted that is waiting on a human before it can execute."""

    tool_name: str
    args: str
    tool_call_id: str


class RunTicketResponse(BaseModel):
    """What the board gets back after asking the agent team to work a ticket."""

    ticket_id: int
    status: TicketStatus
    summary: str | None = None
    requires_human_approval: bool = False
    approval_reason: str | None = None
    delegations: list[str] = Field(default_factory=list)
    pending_approvals: list[PendingApproval] = Field(default_factory=list)


class EventsResponse(BaseModel):
    events: list[AuditEntry] = Field(default_factory=list)


class ApprovePaymentRequest(BaseModel):
    """What a human submits when they click "Approve" on a proposed payment."""

    kind: Literal["invoice", "lease"]
    ref_id: int
    amount: float
    account: str = "checking"
    approved_by: str


class ApprovePaymentResponse(BaseModel):
    paid: bool
    message: str | None = None
    payment_id: int | None = None
    kind: str | None = None
    ref_id: int | None = None
    amount: float | None = None
    account: str | None = None
    approved_by: str | None = None
    paid_at: str | None = None
    new_cash_balance: float | None = None
    invoice_marked_paid: bool | None = None


class CashBalanceResponse(BaseModel):
    found: bool
    account: str | None = None
    balance: float | None = None
    as_of: str | None = None
    message: str | None = None
