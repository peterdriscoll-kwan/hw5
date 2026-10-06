"""FastAPI backend for Campus Customs Operations — the routes a future dashboard will call.

Run from this folder:  uvicorn main:app --reload --port 8000

The agent team (agents.py/orchestrator.py) only ever *prepares* to pay —
make_payment is wrapped with approval_required, so an agent's attempt is
deferred, never executed. The one route in this file that actually moves
money (/api/payments/approve) is the human-triggered action a dashboard's
"Approve" button calls; nothing here lets an agent call it for itself.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic_ai import DeferredToolRequests

from audit import AUDIT_PATH
from models import (
    ApprovePaymentRequest,
    ApprovePaymentResponse,
    CashBalanceResponse,
    EventsResponse,
    PendingApproval,
    RunTicketResponse,
    TicketSummary,
    TicketsResponse,
)
from orchestrator import resolve_ticket

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "mcp_server"))
import server as shop  # noqa: E402 (sys.path must be set before this import)

ORIGINAL_DB = _ROOT / "data" / "campus_customs.db"
WORKING_DB = _ROOT / "data" / "campus_customs_new.db"

app = FastAPI(title="Campus Customs Operations")
app.add_middleware(
    CORSMiddleware,
    # The Vite dashboard dev server — allow it explicitly rather than "*" so the
    # browser will actually let the dashboard call these routes cross-origin.
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/tickets", response_model=TicketsResponse)
def get_tickets() -> TicketsResponse:
    """Route (1): every ticket and whether it's open, in progress, needs approval, or resolved."""
    data = shop.list_tickets()
    tickets = [
        TicketSummary(
            id=t["id"],
            type=t["type"],
            subject=t["subject"],
            requester=t["requester"],
            status=t["status"],
            is_resolved=t["status"] == "resolved",
        )
        for t in data["tickets"]
    ]
    return TicketsResponse(tickets=tickets)


@app.post("/api/tickets/{ticket_id}/run", response_model=RunTicketResponse)
async def run_ticket(ticket_id: int) -> RunTicketResponse:
    """Route (2): run the agent team (starting with the Boss) on one ticket id."""
    ticket = shop.get_ticket(ticket_id)
    if not ticket.get("found"):
        raise HTTPException(status_code=404, detail=f"No ticket found with id {ticket_id}.")
    output = await resolve_ticket(ticket_id)
    if isinstance(output, DeferredToolRequests):
        pending = [
            PendingApproval(tool_name=call.tool_name, args=call.args, tool_call_id=call.tool_call_id)
            for call in output.approvals
        ]
        return RunTicketResponse(ticket_id=ticket_id, status="needs_approval", pending_approvals=pending)
    return RunTicketResponse(
        ticket_id=ticket_id,
        status=output.recommended_status,
        summary=output.summary,
        requires_human_approval=output.requires_human_approval,
        approval_reason=output.approval_reason,
        delegations=output.delegations,
    )


@app.get("/api/events", response_model=EventsResponse)
def get_events(ticket_id: int | None = None, limit: int = 50) -> EventsResponse:
    """Route (3): recent agent events (tool used + what came back), newest first, for the board to poll."""
    if not AUDIT_PATH.exists():
        return EventsResponse(events=[])
    entries = json.loads(AUDIT_PATH.read_text())
    if ticket_id is not None:
        entries = [e for e in entries if e["ticket_id"] == ticket_id]
    recent = list(reversed(entries[-limit:]))
    return EventsResponse(events=recent)


@app.post("/api/payments/approve", response_model=ApprovePaymentResponse)
def approve_payment(payload: ApprovePaymentRequest) -> ApprovePaymentResponse:
    """Route (4): a human clicking "Approve" — the only path that actually moves cash."""
    result = shop.make_payment(
        kind=payload.kind,
        ref_id=payload.ref_id,
        amount=payload.amount,
        account=payload.account,
        approved_by=payload.approved_by,
    )
    return ApprovePaymentResponse(**result)


@app.get("/api/cash", response_model=CashBalanceResponse)
def get_cash() -> CashBalanceResponse:
    """Route (5): the shop's current checking balance."""
    result = shop.get_cash_balance()
    return CashBalanceResponse(**result)


@app.post("/api/reset")
def reset_database() -> dict:
    """Route (6): restore data/campus_customs_new.db from the untouched original, for a fresh run."""
    shutil.copyfile(ORIGINAL_DB, WORKING_DB)
    return {"reset": True, "message": "data/campus_customs_new.db restored from data/campus_customs.db."}
