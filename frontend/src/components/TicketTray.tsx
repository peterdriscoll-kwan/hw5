import type { TicketSummary } from "../types";

const STATUS_LABEL: Record<string, string> = {
  open: "Open",
  in_progress: "In Progress",
  needs_approval: "Needs Approval",
  resolved: "Resolved",
};

interface Props {
  tickets: TicketSummary[];
  selectedId: number | null;
  runningId: number | null;
  onSelect: (id: number) => void;
}

export default function TicketTray({ tickets, selectedId, runningId, onSelect }: Props) {
  return (
    <aside className="tray">
      <h2 className="tray__title">Ticket Tray</h2>
      <p className="tray__hint">Pick a slip off the desk to work it.</p>
      <ul className="tray__list">
        {tickets.map((t) => {
          const isLive = runningId === t.id;
          const badgeClass = isLive ? "live" : t.status;
          const badgeLabel = isLive ? "Agents Working…" : STATUS_LABEL[t.status] ?? t.status;
          return (
            <li key={t.id}>
              <button
                className={`ticket-slip ticket-slip--${isLive ? "in_progress" : t.status} ${selectedId === t.id ? "ticket-slip--selected" : ""}`}
                onClick={() => onSelect(t.id)}
              >
                <span className="ticket-slip__id">#{t.id}</span>
                <span className="ticket-slip__subject">{t.subject}</span>
                <span className="ticket-slip__requester">{t.requester}</span>
                <span className={`status-badge status-badge--${badgeClass}`}>{badgeLabel}</span>
              </button>
            </li>
          );
        })}
      </ul>
    </aside>
  );
}
