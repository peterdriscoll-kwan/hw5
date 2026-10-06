"""The five Campus Customs agents, wired with full peer-to-peer delegation.

Every agent shares the same gated MCP toolset (shop facts and writes come
only from the campus-customs-ops MCP server — never a second, bypassing
data layer) and the same `delegate` tool, so any agent can hand a ticket
to any other agent for help. `make_payment` is wrapped with
`approval_required` on the shared toolset: an agent can attempt it, but
pydantic-ai defers the call for a human instead of executing it, which is
the one real guardrail every agent in this file inherits automatically.
"""

from __future__ import annotations

from pathlib import Path

from pydantic_ai import Agent, DeferredToolRequests, RunContext
from pydantic_ai.mcp import MCPToolset, StdioTransport

from audit import log_run
from models import AgentName, AgentReply, TicketContext
from portkey_client import get_model

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
_PROMPTS = _HERE / "prompts"

_MCP_TRANSPORT = StdioTransport(
    command=str(_ROOT / ".venv" / "bin" / "python3"),
    args=[str(_ROOT / "mcp_server" / "server.py")],
)
_BASE_TOOLSET = MCPToolset(_MCP_TRANSPORT)
# The only tool that moves real money must always be deferred to a human —
# this is enforced here, once, for every agent that shares this toolset.
SHOP_TOOLSET = _BASE_TOOLSET.approval_required(lambda ctx, tool_def, args: tool_def.name == "make_payment")

AGENT_NAMES: tuple[AgentName, ...] = ("boss", "inventory", "accounting", "facilities", "customer_service")

AGENTS: dict[AgentName, Agent[TicketContext, AgentReply | DeferredToolRequests]] = {}


def _make_delegate_tool(self_name: AgentName):
    async def delegate(ctx: RunContext[TicketContext], to_agent: AgentName, message: str) -> str:
        """Hand this ticket to another agent for their expertise and read back what they found.

        `to_agent` must be one of: boss, inventory, accounting, facilities,
        customer_service (not yourself). Pass enough of the ticket's
        context in `message` that the other agent doesn't have to guess —
        they will also call get_ticket themselves, but your message should
        say exactly what you need from them.
        """
        if to_agent == self_name:
            return f"You are {self_name} — you can't delegate to yourself. Make this call yourself instead."
        if to_agent not in AGENTS:
            return f"'{to_agent}' is not a real agent. Choose one of: {', '.join(AGENT_NAMES)}."
        if len(ctx.deps.chain) >= ctx.deps.max_chain_length:
            return (
                f"Delegation limit reached for ticket {ctx.deps.ticket_id} "
                f"(chain so far: {[*ctx.deps.chain, self_name]}). Do not delegate further — "
                "make your own recommendation now, using needs_approval if you're unsure, "
                "rather than bouncing this ticket to another agent."
            )
        sub_deps = TicketContext(
            ticket_id=ctx.deps.ticket_id,
            chain=[*ctx.deps.chain, self_name],
            max_chain_length=ctx.deps.max_chain_length,
        )
        result = await AGENTS[to_agent].run(message, deps=sub_deps)
        log_run(to_agent, ctx.deps.ticket_id, result)
        if isinstance(result.output, DeferredToolRequests):
            pending = ", ".join(call.tool_name for call in result.output.approvals)
            return (
                f"{to_agent} needs human approval before continuing (pending: {pending}). "
                "Nothing was executed — reflect that honestly in your own recommendation."
            )
        reply = result.output
        return (
            f"{to_agent} on ticket {reply.ticket_id}: {reply.summary} "
            f"[recommended_status={reply.recommended_status}, "
            f"requires_human_approval={reply.requires_human_approval}"
            + (f", because {reply.approval_reason}" if reply.approval_reason else "")
            + "]"
        )

    delegate.__name__ = "delegate"
    return delegate


def _build_agent(name: AgentName) -> Agent[TicketContext, AgentReply | DeferredToolRequests]:
    prompt_text = (_PROMPTS / f"{name}.md").read_text()
    return Agent(
        get_model(),
        deps_type=TicketContext,
        output_type=[AgentReply, DeferredToolRequests],
        system_prompt=prompt_text,
        toolsets=[SHOP_TOOLSET],
        tools=[_make_delegate_tool(name)],
        name=name,
    )


for _name in AGENT_NAMES:
    AGENTS[_name] = _build_agent(_name)

BOSS = AGENTS["boss"]
