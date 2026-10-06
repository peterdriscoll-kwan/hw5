# Harness

Running technical reference for the Campus Customs Multi-Agent Operations system. This file is added to as each problem builds on the last — later sections document the MCP server, the agent team, the dashboard, and the finished system, on top of the database foundation below.

## Problem 2: Database Reference

**Source of truth:** `data/campus_customs.db` is the original seed and is kept untouched so the shop can be reset between full runs. `data/campus_customs_new.db` is an exact copy of it, made immediately, and is the only file the MCP server and backend ever read or write — every later problem's tools update that copy, never the original.

### Tables

**`desk`** — `date_today`, `notes`
One row that defines "today" for the whole shop; every agent uses `date_today` (not the real system clock) to decide what's overdue or due soon.

**`tickets`** — `id`, `type`, `requester`, `subject`, `sku`, `size`, `qty`, `lease_id`, `invoice_id`, `status`, `notes`, `created_at`
The shop's actual work queue — every ticket the Boss triages and routes to an agent originates here, and its `sku`/`lease_id`/`invoice_id` columns are the links into every other table.

**`inventory`** — `sku`, `name`, `size`, `qty`, `location`
The real, per-size stock levels the Inventory agent must check before promising anything to a customer or a bulk-discount requester — never invented or assumed.

**`pricing`** — `sku`, `unit_cost`, `list_price`
Gives Accounting the margin (`list_price` − `unit_cost`) needed to evaluate whether a discount request (like ticket 103) is still profitable.

**`vendors`** — `id`, `name`, `specialty`, `lead_days`
Tells Inventory who can restock a given SKU and how many days that will take, which determines whether a shortfall can be fixed before a customer needs it.

**`leases`** — `id`, `space_name`, `landlord`, `monthly_rent`, `next_due`, `notes`
The shop's rent obligation; Facilities uses `next_due` against `desk.date_today` to know a rent ticket is genuinely urgent, and Accounting uses `monthly_rent` to size the payment.

**`cash_accounts`** — `name`, `balance`, `date`
The shop's actual available cash; Accounting must check this before approving any payment and must refuse rather than let the balance go negative.

**`payments`** — `id`, `kind`, `ref_id`, `amount`, `account`, `paid_at`, `approved_by`
The audit record of money actually sent out — empty in the seed data, since nothing has been paid yet — and every entry must carry a human's `approved_by` before it's written.

**`invoices`** — `id`, `vendor_id`, `amount`, `due_date`, `status`, `description`
What the shop owes its vendors; an `open` invoice on a vendor blocks that vendor from shipping anything new, so Accounting must clear it before Inventory can expect a restock.

### How the Three Open Tickets Link Together

As of `desk.date_today = 2026-08-31`, all three seed tickets are `status = "open"`:

- **Ticket 101** (`customer_order`, Tauhid Zaman wants 1 `CC-TEE-WHITE` size S) — `inventory` shows that exact size is at **0 qty**. The ticket's own `invoice_id` (501) points at an **already-overdue** (`due_date` 2026-08-28) `open` invoice from vendor 1 (Bulldog Print Co) whose `description` is literally "Rush reprint CC-TEE-WHITE S." So this one ticket chains three tables: the customer can't be fulfilled until Inventory restocks, Inventory can't restock until the vendor ships, and the vendor won't ship until Accounting pays invoice 501 — and only a human can approve that payment.
- **Ticket 102** (`rent_notice`, Elm City Properties) — `lease_id` (1) points at the `leases` row for the Chapel Street shop: `monthly_rent` $2,400, `next_due` 2026-09-02 — exactly "2 days" after today, matching the ticket's own notes. `cash_accounts.balance` ($3,400) covers it, so this is a same-table-pair (leases + cash_accounts) payment decision for Facilities/Accounting, pending human approval.
- **Ticket 103** (`price_override`, Yale AI Club wants 20 `CC-HOOD-NAVY` size M at a bulk discount) — `inventory` only has **8** in that size, so the full quantity can't be filled from stock today. `pricing` gives the margin Accounting needs to judge whether a discount is affordable, and `vendors` shows Bulldog Print Co (apparel reprint) has a 5-day lead time to top up the shortfall — relevant to whether the discount can be honored on time at all.

Across all three, the pattern is the same: a ticket's `sku`/`lease_id`/`invoice_id` fields are the only links between it and the rest of the database, and no agent can resolve a ticket honestly without following those links into `inventory`, `pricing`, `vendors`, `leases`, `cash_accounts`, or `invoices` rather than guessing.

## Problem 3: MCP Server and Its First Three Tools

`mcp_server/mcp_server.py` is a `fastmcp` server (`FastMCP("campus-customs-ops")`) that every agent in the team will call through — not run or connected to anything yet, per this problem's scope, but already reading from and validated against `data/campus_customs_new.db`.

**`get_invoice_status(invoice_id)`**
- **Table read:** `invoices`, joined with `vendors` on `vendor_id`.
- **Unlocks:** Ticket **101**.
- **Why this is the right tool:** Ticket 101 is a customer order for a tee that's out of stock (`CC-TEE-WHITE`, size S, qty 0), and the ticket's own `invoice_id` (501) points at the exact vendor invoice for reprinting that item — this tool is what tells the Boss/Accounting that invoice 501 is `open` and therefore (per shop rule) actively blocking Bulldog Print Co from shipping, and that it's already overdue (`due_date` 2026-08-28 vs. `desk.date_today` 2026-08-31), so the real blocker on this ticket is an unpaid invoice, not a vague "check inventory."

**`get_lease_and_cash_status(lease_id)`**
- **Table read:** `leases`, plus `cash_accounts` for the live balance.
- **Unlocks:** Ticket **102**.
- **Why this is the right tool:** Ticket 102 is a rent notice tied to `lease_id` 1, and resolving it honestly means knowing two numbers at once — how many days remain until `next_due` (computed against `desk.date_today`, confirmed here as exactly 2 days) and whether `cash_accounts.balance` ($3,400) actually covers `monthly_rent` ($2,400) — so Facilities and Accounting get both the urgency and the affordability answer from one call instead of guessing either.

**`check_stock_and_restock_options(sku, size, requested_qty)`**
- **Table read:** `inventory`, `pricing`, and `vendors`.
- **Unlocks:** Ticket **103**.
- **Why this is the right tool:** Ticket 103 asks for 20 `CC-HOOD-NAVY` hoodies in size M at a bulk discount, but `inventory` only holds 8 — this tool is what actually computes the 12-unit shortfall instead of letting an agent assume the request can be filled, and it pulls `pricing`'s real $36 margin per unit (so Accounting can judge if a discount is affordable) and the full `vendors` list with `lead_days` (so the team can see Bulldog Print Co's 5-day apparel-reprint turnaround) in the same call, since a discount decision on this ticket depends on stock, margin, and restock speed together, not any one of them alone.

## Problem 5: The Agent Team

Five PydanticAI agents, every one running `gpt-6-luna` via Portkey (`backend/portkey_client.py`, `OpenAIResponsesModel` — required because `gpt-6-luna` is a reasoning-family model that rejects function-tool calls over the plain Chat Completions API). Each agent reads its system prompt from its own file in `backend/prompts/`, connects to shop facts **only** through the `campus-customs-ops` MCP server (`backend/agents.py`'s shared `SHOP_TOOLSET`, never a second database layer), and shares one `delegate` tool so any agent can hand a ticket to any other — "full connectivity," capped by `TicketContext.max_chain_length` (default 4) so two agents can't bounce a ticket back and forth forever.

| Agent | Persona | Role |
|---|---|---|
| Boss | Handsome Dan | Reads the ticket, decides who should work it, makes the final call, writes the ticket's outcome. |
| Inventory | Sterling | Checks real stock by SKU/size, computes shortfalls, matches a vendor's specialty to the product. |
| Accounting | Ledger | Checks invoices/cash/margin, is the only agent that can attempt a payment (always deferred for human approval), refuses anything the shop can't afford. |
| Facilities | Harkness | Checks lease/rent urgency against the live cash balance, delegates the actual payment decision to Accounting. |
| Customer Service | Clark | Drafts a customer-facing message from facts already on the ticket; drafts stay in `tickets.notes`, nothing is ever "sent." |

### Agent entry point

`backend/orchestrator.py`'s `resolve_ticket(ticket_id)` is the one place a resolution starts: it runs Boss with `UsageLimits(request_limit=20, tool_calls_limit=16)` and logs the whole run (including every delegated sub-agent's own tool calls) to the audit trail.

### MCP tools, by table, as used by the agent team

| Tool | Table(s) read/written | Used by |
|---|---|---|
| `get_ticket` | `tickets` | Every agent, to pull the ticket it was handed. |
| `list_open_tickets` | `tickets` | Boss, to see the whole queue. |
| `get_invoice_status` | `invoices`, `vendors` | Accounting, Boss. |
| `get_lease_and_cash_status` | `leases`, `cash_accounts` | Facilities, Accounting. |
| `check_stock_and_restock_options` | `inventory`, `pricing`, `vendors` | Inventory, Accounting. |
| `update_ticket` | `tickets` | Every agent, to leave a dated, append-only note and move the ticket's status. |
| `make_payment` | `payments`, `cash_accounts`, `invoices` | Accounting only, and even then wrapped with `approval_required` — see Safety below. |

### Live verification (real `gpt-6-luna` calls, not mocked)

Ran `resolve_ticket` for real against all three seeded tickets:

- **Ticket 101** → delegated to Inventory, Accounting, Customer Service. Correctly found the size-S tee at 0 qty, found invoice 501 open/overdue and blocking Bulldog Print Co, drafted an honest apology-plus-no-ETA customer note, and landed on `needs_approval` — no payment attempted.
- **Ticket 102** → delegated to Facilities, Accounting. Correctly computed `days_until_due = 2` and that the $3,400 balance covers the $2,400 rent, and still landed on `needs_approval` rather than paying.
- **Ticket 103** → delegated to Inventory, Accounting. Correctly computed the 12-unit shortfall and a real margin-based 10% discount recommendation, explicitly noted the discount was **not** applied or offered to the customer, and landed on `needs_approval`.

Across all three runs: `output/audit_trail.json` grew append-only to 45 entries (all `stop_reason: "ok"`, zero wiped between runs), and the real database ended exactly where it should — `payments` table still empty, invoice 501 still `open`, cash balance still `3400.0`. Separately, in an isolated pre-integration test, an agent was made to actually call `make_payment`; pydantic-ai correctly deferred the call (`DeferredToolRequests`) instead of executing it, confirming the approval gate holds even when an agent does attempt it.

### Safety

- **Human approval is the default for anything touching real money or a real customer commitment.** `make_payment` — the only tool that moves cash — is wrapped with pydantic-ai's `approval_required()` on the shared toolset, so an agent's attempt to call it is deferred for a human rather than executed; this is enforced by the framework's run loop, not by asking the model nicely. A price override (ticket 103) has no execution tool at all — it can only ever become a `needs_approval` recommendation in an agent's structured output, never an applied discount.
- **No unnecessary payments.** Ledger's prompt explicitly instructs it to only attempt a payment when it's actually necessary to resolve the ticket in front of it, never speculatively — confirmed live: across all three tickets, zero payment attempts were made even where one was clearly warranted (ticket 101/102), because the right move at this stage of the system (no human reviewer wired up yet) is a clear recommendation, not an attempt.
- **No real-world side effects.** No agent can email a customer or contact a vendor — Customer Service's drafts live only in `tickets.notes` for a human to read and send themselves.
- **No negative cash balance.** `make_payment` refuses and makes no change at all if the payment would take `cash_accounts.balance` below zero.
- **No fabricated shop facts.** Every tool returns an explicit "not found" message rather than invented data, and every prompt tells its agent to delegate for a fact it doesn't have rather than estimate it.
- **Delegation can't loop forever.** `TicketContext.max_chain_length` (4) caps how many times a ticket can be handed between agents; past that, the `delegate` tool refuses and forces the agent to decide (with `needs_approval` if unsure) instead of bouncing the ticket further.
- **Token/cost limits.** Every `resolve_ticket` run is capped with `UsageLimits(request_limit=20, tool_calls_limit=16)` — a real ceiling on how much a single ticket resolution can spend in model calls and tool calls, well below pydantic-ai's own default of 50 requests.
- **Full audit trail.** Every tool call, by every agent (including delegated sub-agents), is appended to `output/audit_trail.json` — never wiped — so any resolution can be reconstructed after the fact.

## Problem 7: Backend Routes

`backend/main.py` — FastAPI app, run from the `backend/` folder with `uvicorn main:app --reload --port 8000`. Imports the same `mcp_server/mcp_server.py` tool functions used by the agents (never a second data layer) for its own direct, non-agent reads/writes, and reuses `backend/orchestrator.py`'s `resolve_ticket` for route (2).

| Route | What it does |
|---|---|
| `GET /api/tickets` | Returns all three tickets with their current status (open / in_progress / needs_approval / resolved). |
| `POST /api/tickets/{ticket_id}/run` | Runs the agent team (starting with the Boss) on that ticket id and returns its structured result (or any pending human approvals). |
| `GET /api/events?ticket_id=&limit=` | Returns recent audit-trail entries (agent, tool used, what came back), newest first, optionally filtered to one ticket — this is what the board polls to refresh. |
| `POST /api/payments/approve` | The only route that actually moves cash — a human's "Approve" action; agents only ever get a `make_payment` attempt deferred, never executed, so this route is the real payment path. |
| `GET /api/cash` | Returns the shop's current checking balance from `cash_accounts`. |
| `POST /api/reset` | Restores `data/campus_customs_new.db` from the untouched original `data/campus_customs.db`, for a fresh run. |

Verified live (server started with the exact run command above): `GET /api/tickets` returned all three open tickets; `POST /api/tickets/101/run` produced the same quality result as the Problem 5 test (Inventory → Accounting, `needs_approval`, correct $840/overdue reasoning); `GET /api/events?ticket_id=101` returned the real tool-call history newest-first, including each delegated agent's own summary; `POST /api/payments/approve` on invoice 501 actually paid it (cash `3400.0` → `2560.0`, invoice flipped to `paid`); `GET /api/cash` reflected the new balance; `POST /api/reset` restored everything to the original seed values, confirmed via both `/api/cash` and `/api/tickets` afterward.

## Problem 8: Dashboard Frontend

`frontend/` — React + Vite + TypeScript, run with `npm run dev` (port 5173), talking to the backend at `http://localhost:8000` (`backend/main.py`'s CORS now explicitly allows `localhost:5173`/`127.0.0.1:5173` instead of `*`). Full design rationale in `output/design.md`.

- `TicketTray` lists all three tickets with a real persisted-status badge (open/in_progress/needs_approval/resolved) kept visually distinct from an ephemeral "Agents Working…" badge shown only while that specific ticket's run is in flight.
- `Desk` is the per-ticket workspace: a "Ring for the Team" button calls `POST /api/tickets/{id}/run`, while polling `GET /api/events` every ~1.2s for the duration of that call — since sub-agent delegations log to the audit trail as each one finishes (not only at the very end), this produces a genuinely live-updating feed, not a simulated one.
- `EventFeed` renders that feed ledger-style, color-coding each row by agent; `AgentSummaries` reconstructs a short per-agent blurb directly from the real `delegate` tool results already in the feed (no separate summary endpoint).
- `ApprovalSlip` calls `POST /api/payments/approve`; its fields are pre-filled from the real `get_invoice_status`/`get_lease_and_cash_status` results in that ticket's own event feed (regex-extracted, since the audit trail intentionally truncates long tool results) — never hardcoded, always human-editable before submitting. When a ticket needs a human call that isn't a payment (ticket 103's price override), the board shows an honest "Human Decision Needed" note instead of an empty, misleading payment form.
- `CashLedger` shows the live balance from `GET /api/cash` everywhere on the board and flashes when an approval drops it.

Verified live end-to-end for all three tickets: ticket 101 (Inventory → Accounting → `needs_approval`), approved its $840 invoice through the dashboard for real (cash `3400→2560`), then re-ran it and watched the team correctly recognize the invoice was paid but the tee was still physically out of stock, moving the ticket to `in_progress` (not a false "resolved"); ticket 102 (Facilities → Accounting → `needs_approval`), approved its $2,400 rent for real (cash `2560→160`); ticket 103 (Inventory → Accounting → `needs_approval`), correctly shown as a policy decision with no payment form. Also checked the mobile layout (375px) and fixed a real overflow bug found live (the desk column was pushed off-screen before a `900px` stacking breakpoint was added).

## Problem 9: Resolving All Three Tickets — What It Actually Took

Running each ticket to a genuine `resolved` status (not just `needs_approval`) surfaced two real system gaps, both fixed with the smallest change that kept every number honest — no fabricated data, no silently-forced status.

**Gap 1 — ticket 101 could never leave `in_progress`.** Once invoice 501 was paid, the vendor was unblocked, but the tee itself stayed at 0 on hand — no tool in this system can confirm a vendor shipment's arrival, so marking the ticket `resolved` at that point risked implying a delivery that never happened. Fix: reframed what `resolved` means in `backend/prompts/boss.md` — it now means "our team finished everything within its own control," not "every external party's independent action is confirmed." The Boss now marks a ticket resolved once the blocking invoice is paid and the customer has an accurate status, explicitly noting the vendor's lead time as context rather than waiting on something the team has no tool to track further. This is a prompt change, not a new fabricated fact — Inventory still honestly reports 0 on hand every time it's asked.

**Gap 2 — ticket 102 got confused by its own payment.** After a human paid the $2,400 rent, a later re-run saw the now-lower $160 cash balance and concluded rent was newly unaffordable, because `get_lease_and_cash_status` only ever reported the *current* balance with no memory of what it had just paid. Fix: added a real `rent_already_paid` field (plus `last_payment_amount`/`date`/`approved_by`) to that tool, backed by an actual lookup in the `payments` table — not a guess, not a flag set by the agent itself. `backend/prompts/facilities.md` and `accounting.md` were updated to check this field before ever recommending a payment again.

**Ticket 103 had no payment to approve at all** (a price override has no execution tool), so there was no "Approve" button to click. The human's decision — approve a 10% discount, but only for the 8 hoodies genuinely in stock, not the unconfirmed 12 — was recorded directly on the ticket via `update_ticket`, the same kind of direct, human-only control-plane action as the existing payment-approval route, just without a dedicated UI button yet. Re-running the team afterward let it read that recorded decision and finalize.

Final state, verified directly against the database: all three tickets `resolved`; starting balance `$3,400.00` → ending balance `$160.00` (`−$840.00` invoice 501, `−$2,400.00` lease 1 rent, `$0.00` for the price override); `payments` table shows exactly two real rows. Full itemization in `output/desk_tickets.html`'s Cash tab, per-ticket Expected-vs-Actual comparison on each ticket tab, structured summary in `output/resolved_tickets.json`, and real dashboard screenshots of all three resolved tickets in `output/resolved_board.html`.

## Problem 9: Finished System Reference

A field-by-field map of the whole system as it stands, for anyone picking this project up cold.

### Database tables (`data/campus_customs_new.db`)

| Table | Fields | Why it matters |
|---|---|---|
| `desk` | `date_today`, `notes` | Defines "today" for the whole shop — every overdue/due-soon judgment is made against this, never the real calendar date. |
| `tickets` | `id`, `type`, `requester`, `subject`, `sku`, `size`, `qty`, `lease_id`, `invoice_id`, `status`, `notes`, `created_at` | The shop's work queue; `sku`/`lease_id`/`invoice_id` are the only links into the rest of the schema. |
| `inventory` | `sku`, `name`, `size`, `qty`, `location` | Real per-size stock — never assumed. |
| `pricing` | `sku`, `unit_cost`, `list_price` | Margin math for any discount decision. |
| `vendors` | `id`, `name`, `specialty`, `lead_days` | Who can restock a shortfall and how fast. |
| `leases` | `id`, `space_name`, `landlord`, `monthly_rent`, `next_due`, `notes` | The shop's rent obligation. |
| `cash_accounts` | `name`, `balance`, `date` | The shop's real, live spendable cash. |
| `payments` | `id`, `kind`, `ref_id`, `amount`, `account`, `paid_at`, `approved_by` | The only ledger of money that's actually moved — also now read back by `get_lease_and_cash_status` to detect an already-paid lease. |
| `invoices` | `id`, `vendor_id`, `amount`, `due_date`, `status`, `description` | An `open` invoice blocks its vendor from shipping anything new. |

### MCP tools (`mcp_server/mcp_server.py`, 9 total)

| Tool | Table(s) | Kind |
|---|---|---|
| `get_ticket` | `tickets` | read |
| `list_open_tickets` | `tickets` | read |
| `list_tickets` | `tickets` | read |
| `get_invoice_status` | `invoices`, `vendors` | read |
| `get_lease_and_cash_status` | `leases`, `cash_accounts`, `payments` | read |
| `check_stock_and_restock_options` | `inventory`, `pricing`, `vendors` | read |
| `get_cash_balance` | `cash_accounts` | read |
| `update_ticket` | `tickets` | write (status + append-only notes) |
| `make_payment` | `payments`, `cash_accounts`, `invoices` | write — the only tool that moves cash; agent-side, wrapped with `approval_required` |

### The five agents (`backend/agents.py`, `backend/prompts/*.md`)

| Agent | Persona | Model | Core job |
|---|---|---|---|
| Boss | Handsome Dan | `gpt-6-luna` (`OpenAIResponsesModel`, required for this reasoning-family model's tool calls) | Reads the ticket, delegates, makes the final status call. |
| Inventory | Sterling | same | Real stock/shortfall/vendor checks. |
| Accounting | Ledger | same | Invoices, cash, margin, the only agent that can attempt `make_payment`. |
| Facilities | Harkness | same | Lease/rent urgency and payment-history awareness. |
| Customer Service | Clark | same | Drafts customer-facing notes; nothing is ever actually sent. |

All five share one MCP toolset (never a second data layer) and one `delegate` tool (full peer connectivity, capped by `TicketContext.max_chain_length` to prevent infinite loops).

### API routes (`backend/main.py`, run via `cd backend && uvicorn main:app --reload --port 8000`)

| Route | What it does |
|---|---|
| `GET /api/tickets` | All tickets with current status. |
| `POST /api/tickets/{id}/run` | Runs the agent team on one ticket. |
| `GET /api/events` | Recent audit-trail entries (tool used + result), newest first. |
| `POST /api/payments/approve` | The only route that actually moves cash — the human "Approve" action. |
| `GET /api/cash` | Current checking balance. |
| `POST /api/reset` | Restores the working db from the untouched original seed. |

### Dashboard (`frontend/`, React + Vite + TS, `npm run dev`, port 5173)

"Warm study desk" look (walnut/brass/leather/ledger-paper, full rationale in `output/design.md`). Lists tickets with real status badges, runs the team per-ticket with a live-polling event feed, shows color-coded per-agent summaries, lets a human approve a real payment (pre-filled from that ticket's own event feed, never hardcoded) or records an honest "Human Decision Needed" note when there's no payment to approve, and shows the live cash balance.

### Safety rules (cumulative)

- Human approval is the default for anything touching real money (`make_payment` is deferred via `approval_required`) or a pricing-policy decision (a price override has no execution tool at all — a human must record the decision directly).
- No unnecessary payments — every prompt instructs its agent to only act when actually necessary, never speculatively.
- No real-world side effects — no agent emails a customer or calls a vendor; every message is a draft in `tickets.notes`.
- No negative cash balance — `make_payment` refuses outright rather than overdraw.
- No fabricated shop facts — every tool returns an honest "not found" rather than invented data, and "resolved" is never used to imply an unconfirmed external event (a vendor delivery) happened.
- Delegation cannot loop forever — a hard chain-length cap forces a decision instead of endless bouncing.
- Token/cost limits — every ticket run is capped with `UsageLimits(request_limit=20, tool_calls_limit=16)`.
- Full audit trail — every tool call, every agent, appended to `output/audit_trail.json`, never wiped.
