import type { AuditEvent } from "../types";
import { personaFor } from "../agents";

interface Props {
  events: AuditEvent[];
}

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  } catch {
    return iso;
  }
}

export default function EventFeed({ events }: Props) {
  if (events.length === 0) {
    return <p className="ledger__empty">No activity yet on this ticket — ring for the team below.</p>;
  }
  // oldest first, like a ledger growing down the page
  const chronological = [...events].reverse();
  return (
    <ol className="ledger">
      {chronological.map((e, i) => {
        const persona = personaFor(e.agent);
        const isDeferred = e.stop_reason === "deferred_approval";
        return (
          <li key={i} className={`ledger__row ${isDeferred ? "ledger__row--deferred" : ""}`}>
            <span className="ledger__nameplate" style={{ background: persona.accent }}>
              {persona.initials}
            </span>
            <div className="ledger__body">
              <div className="ledger__meta">
                <b>{persona.name}</b> <span className="ledger__role">({persona.role})</span>
                <span className="ledger__time">{formatTime(e.timestamp)}</span>
              </div>
              <div className="ledger__tool">
                called <code>{e.tool_name}</code>
                {isDeferred && <span className="ledger__flag"> — awaiting human approval</span>}
              </div>
              <div className="ledger__result">{e.short_result}</div>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
