# Campus Customs Operations MCP Server

An MCP server (built with `fastmcp`) that gives every agent in the Campus
Customs team — Handsome Dan (Boss), Sterling (Inventory), Ledger
(Accounting), Harkness (Facilities), Clark (Customer Service) — one
shared, consistent way to read and update the real shop data instead of
each agent reaching into the database (or guessing) on its own.

**Database:** `data/campus_customs_new.db` (the working copy — the original
`data/campus_customs.db` is never touched, so the shop can be reset by
re-copying it over the working file).

Connected to this project via `.mcp.json` (`campus-customs-ops`) and, for
the agent team itself, via a `pydantic_ai.mcp.MCPToolset`/`StdioTransport`
pointed at this file — the agents never read the database directly.

## Tools

**Shop-fact lookups (read-only):**

- **`get_invoice_status(invoice_id)`** — vendor invoice (amount, due date,
  status, the vendor it belongs to), flagging whether it's blocking that
  vendor from shipping and whether it's overdue. Unlocks ticket 101.
- **`get_lease_and_cash_status(lease_id)`** — a lease's rent amount and
  due date alongside the shop's live cash balance; reports days until due
  and whether the balance covers it, plus `rent_already_paid` (backed by
  a real lookup in the `payments` table, not a guess) so a later check
  doesn't mistake "cash is lower now" for "rent still unpaid." Unlocks
  ticket 102.
- **`check_stock_and_restock_options(sku, size, requested_qty)`** — real
  on-hand quantity, the shortfall against a requested quantity, real
  unit cost/list price margin, and every vendor (specialty + lead time).
  Unlocks ticket 103.
- **`list_open_tickets()`** — every open ticket, for the Boss to triage
  the active queue.
- **`list_tickets()`** — every ticket regardless of status, for the
  dashboard's full board view.
- **`get_ticket(ticket_id)`** — one ticket's full record, for any agent
  working it or receiving a delegation.
- **`get_cash_balance()`** — the shop's current checking balance, for the
  dashboard's cash display.

**Shop-fact writes:**

- **`update_ticket(ticket_id, status, note)`** — moves a ticket to a new
  status (`open` / `in_progress` / `needs_approval` / `resolved`) and
  appends a dated note; never overwrites existing notes.
- **`make_payment(kind, ref_id, amount, account, approved_by)`** — the
  only tool that moves real shop cash (pays a vendor invoice or a
  lease's rent), refusing outright if it would take the cash balance
  negative. On the agent side this tool is wrapped with
  `approval_required`, so an agent attempting it gets the call deferred
  for a human instead of executed — it is never silently completed.

Every tool reads straight from the database and returns an honest
"not found" message rather than inventing a row, a price, or a quantity
that isn't actually there.
