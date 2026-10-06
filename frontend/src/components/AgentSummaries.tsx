import type { AuditEvent } from "../types";
import { personaFor } from "../agents";

interface Props {
  events: AuditEvent[];
  bossSummary: string | null;
}

interface Extracted {
  agentKey: string;
  text: string;
}

// Every delegate call's result reads "<agent> on ticket N: <summary> [recommended_status=...]" —
// pull just the human-readable summary back out for a short, per-agent card.
function extractDelegateSummaries(events: AuditEvent[]): Extracted[] {
  const out: Extracted[] = [];
  for (const e of events) {
    if (e.tool_name !== "delegate") continue;
    const match = e.short_result.match(/^(\w+) on ticket \d+: (.+?)(?: \[recommended_status=.*)?$/s);
    if (match) {
      out.push({ agentKey: match[1], text: match[2].replace(/…$/, "…") });
    }
  }
  return out;
}

export default function AgentSummaries({ events, bossSummary }: Props) {
  const delegateSummaries = extractDelegateSummaries(events);
  if (delegateSummaries.length === 0 && !bossSummary) {
    return null;
  }
  return (
    <div className="summary-cards">
      {bossSummary && (
        <div className="index-card" style={{ borderColor: personaFor("boss").accent }}>
          <div className="index-card__who" style={{ color: personaFor("boss").accent }}>
            {personaFor("boss").name} · {personaFor("boss").role}
          </div>
          <p className="index-card__text">{bossSummary}</p>
        </div>
      )}
      {delegateSummaries.map((s, i) => {
        const persona = personaFor(s.agentKey);
        return (
          <div className="index-card" key={i} style={{ borderColor: persona.accent }}>
            <div className="index-card__who" style={{ color: persona.accent }}>
              {persona.name} · {persona.role}
            </div>
            <p className="index-card__text">{s.text}</p>
          </div>
        );
      })}
    </div>
  );
}
