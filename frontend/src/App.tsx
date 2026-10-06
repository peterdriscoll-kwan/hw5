import { useEffect, useState } from "react";
import type { CashBalance, TicketSummary } from "./types";
import { getCashBalance, getTickets, resetDatabase } from "./api";
import TicketTray from "./components/TicketTray";
import Desk from "./components/Desk";
import CashLedger from "./components/CashLedger";
import "./App.css";

export default function App() {
  const [tickets, setTickets] = useState<TicketSummary[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [runningId, setRunningId] = useState<number | null>(null);
  const [cash, setCash] = useState<CashBalance | null>(null);

  function refreshTickets() {
    getTickets().then((r) => {
      setTickets(r.tickets);
      setSelectedId((prev) => prev ?? r.tickets[0]?.id ?? null);
    });
  }

  function refreshCash() {
    getCashBalance().then(setCash);
  }

  useEffect(() => {
    refreshTickets();
    refreshCash();
  }, []);

  const selected = tickets.find((t) => t.id === selectedId) ?? null;

  return (
    <div className="study">
      <header className="study__header">
        <div className="study__wordmark">
          <span className="study__crest">CC</span>
          <div>
            <h1>Campus Customs</h1>
            <p>Agent Desk — Operations Board</p>
          </div>
        </div>
        <div className="study__header-right">
          <CashLedger balance={cash?.balance ?? null} asOf={cash?.as_of ?? null} />
          <button
            className="reset-link"
            onClick={() => {
              resetDatabase().then(() => {
                refreshTickets();
                refreshCash();
              });
            }}
            title="Restore the database to its original seed values"
          >
            ↺ Reset demo data
          </button>
        </div>
      </header>

      <main className="study__floor">
        <TicketTray
          tickets={tickets}
          selectedId={selectedId}
          runningId={runningId}
          onSelect={setSelectedId}
        />
        {selected ? (
          <Desk
            key={selected.id}
            ticket={selected}
            onTicketChanged={refreshTickets}
            onRunningChange={setRunningId}
            onCashChanged={refreshCash}
          />
        ) : (
          <div className="desk desk--empty">Loading the ticket tray…</div>
        )}
      </main>
    </div>
  );
}
