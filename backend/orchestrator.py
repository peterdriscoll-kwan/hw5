"""Entry point for resolving one ticket end-to-end: the Boss, from scratch.

This is deliberately the only place a ticket resolution starts — the Boss
reads the ticket, delegates to whichever specialists it needs (who can
delegate further, within the chain limit), and the whole run's tool
activity (including every delegated sub-agent's own tool calls) ends up
in output/audit_trail.json.

Loop limits here are a real safety control, not a formality:
request_limit/tool_calls_limit cap how much a single ticket resolution
can spend in model calls and tool calls, and TicketContext.max_chain_length
caps how many times agents can hand a ticket to each other before being
forced to decide instead of delegating again.
"""

from __future__ import annotations

from pydantic_ai import DeferredToolRequests, UsageLimits

from agents import BOSS
from audit import log_error, log_run
from models import AgentReply, TicketContext


async def resolve_ticket(ticket_id: int) -> AgentReply | DeferredToolRequests:
    deps = TicketContext(ticket_id=ticket_id)
    limits = UsageLimits(request_limit=20, tool_calls_limit=16)
    try:
        result = await BOSS.run(
            f"A ticket (id {ticket_id}) needs to be worked. Pull it with get_ticket, "
            "decide who needs to be involved, and resolve it as far as you honestly can.",
            deps=deps,
            usage_limits=limits,
        )
    except Exception as error:  # noqa: BLE001 - this is the top-level safety net for the whole run
        log_error("boss", ticket_id, error)
        raise
    log_run("boss", ticket_id, result)
    return result.output
