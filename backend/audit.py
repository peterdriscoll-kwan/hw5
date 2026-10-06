"""Append-only audit trail for every agent-loop tool call.

Walks a finished agent run's message history, pairs each real tool call
with its return value, and appends one row per call to
output/audit_trail.json under a lock. The file is read and rewritten with
the new rows added — it is never truncated or recreated, so history from
every previous run (including previous process runs) survives.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic_ai import DeferredToolRequests
from pydantic_ai.agent import AgentRunResult
from pydantic_ai.messages import ModelMessage, ToolCallPart, ToolReturnPart

from models import AuditEntry

_ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = _ROOT / "output" / "audit_trail.json"
_LOCK = threading.Lock()


def _short(value: Any, limit: int = 300) -> str:
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    text = text.strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def build_entries(agent_name: str, ticket_id: int, messages: list[ModelMessage]) -> list[AuditEntry]:
    """Pair every tool-call part with its tool-return part across the message history."""
    calls: dict[str, ToolCallPart] = {}
    entries: list[AuditEntry] = []
    for message in messages:
        for part in message.parts:
            if isinstance(part, ToolCallPart):
                calls[part.tool_call_id] = part
            elif isinstance(part, ToolReturnPart):
                call = calls.get(part.tool_call_id)
                if call is None or call.tool_name == "final_result":
                    continue
                entries.append(
                    AuditEntry(
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        ticket_id=ticket_id,
                        agent=agent_name,
                        tool_name=call.tool_name,
                        short_args=_short(call.args),
                        short_result=_short(part.content),
                        stop_reason="ok",
                    )
                )
    return entries


def append_audit(entries: list[AuditEntry]) -> None:
    if not entries:
        return
    with _LOCK:
        existing: list[dict] = []
        if AUDIT_PATH.exists():
            existing = json.loads(AUDIT_PATH.read_text())
        existing.extend(entry.model_dump() for entry in entries)
        AUDIT_PATH.write_text(json.dumps(existing, indent=2))


def log_run(agent_name: str, ticket_id: int, result: AgentRunResult) -> None:
    """Build and append audit entries for a finished agent run, including a deferred-approval marker."""
    entries = build_entries(agent_name, ticket_id, result.all_messages())
    if isinstance(result.output, DeferredToolRequests):
        for call in result.output.approvals:
            entries.append(
                AuditEntry(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    ticket_id=ticket_id,
                    agent=agent_name,
                    tool_name=call.tool_name,
                    short_args=_short(call.args),
                    short_result="Deferred — awaiting human approval before this call can execute.",
                    stop_reason="deferred_approval",
                )
            )
    append_audit(entries)


def log_error(agent_name: str, ticket_id: int, error: Exception) -> None:
    append_audit(
        [
            AuditEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                ticket_id=ticket_id,
                agent=agent_name,
                tool_name="(agent run)",
                short_args="",
                short_result=_short(f"{type(error).__name__}: {error}"),
                stop_reason="error",
            )
        ]
    )
