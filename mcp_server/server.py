"""Campus Customs Operations MCP — read/write access to the shop database.

Every agent in the Boss/Inventory/Accounting/Facilities/Customer Service
team talks to the shop through this one MCP server, so tools live here
rather than duplicated per-agent. All tools read ../data/campus_customs_new.db
(the working copy) and never the original data/campus_customs.db, so the
shop can always be reset by re-copying the original over the working file.

Tools never invent a number that isn't in the database: if a lookup finds
nothing, the tool says so explicitly instead of guessing or defaulting to
zero.

Run from this folder (stdio):  python server.py
Run (HTTP):                    python server.py --http
HTTP URL:                       http://127.0.0.1:8002/mcp
"""

from __future__ import annotations

import argparse
import sqlite3
from datetime import date
from pathlib import Path

from fastmcp import FastMCP

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DB_PATH = ROOT / "data" / "campus_customs_new.db"

mcp = FastMCP("campus-customs-ops")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _today() -> date:
    with _connect() as conn:
        row = conn.execute("SELECT date_today FROM desk LIMIT 1").fetchone()
    return date.fromisoformat(row["date_today"])


@mcp.tool
def get_invoice_status(invoice_id: int) -> dict:
    """Look up a vendor invoice and whether it is blocking that vendor from shipping.

    Resolves ticket 101: the customer wants a tee that is out of stock, and
    the ticket's own invoice_id points at the vendor invoice for reprinting
    exactly that item. A vendor will not ship new product while they still
    have an open unpaid invoice, so Accounting/Boss need this tool to see
    the invoice's amount, due_date, status, and the vendor it blocks before
    deciding whether a payment needs human approval. Never invents an
    invoice — if the id doesn't exist, says so.
    """
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT i.id, i.vendor_id, i.amount, i.due_date, i.status, i.description,
                   v.name AS vendor_name, v.specialty AS vendor_specialty, v.lead_days
            FROM invoices i
            JOIN vendors v ON v.id = i.vendor_id
            WHERE i.id = ?
            """,
            (invoice_id,),
        ).fetchone()
    if row is None:
        return {"invoice_id": invoice_id, "found": False, "message": f"No invoice found with id {invoice_id}."}
    today = _today()
    overdue = row["status"] == "open" and date.fromisoformat(row["due_date"]) < today
    return {
        "invoice_id": row["id"],
        "found": True,
        "amount": row["amount"],
        "due_date": row["due_date"],
        "status": row["status"],
        "description": row["description"],
        "vendor_id": row["vendor_id"],
        "vendor_name": row["vendor_name"],
        "vendor_specialty": row["vendor_specialty"],
        "vendor_lead_days": row["lead_days"],
        "blocks_vendor_shipping": row["status"] == "open",
        "overdue": overdue,
        "today": today.isoformat(),
    }


@mcp.tool
def get_lease_and_cash_status(lease_id: int) -> dict:
    """Look up a lease's rent due date alongside the shop's current cash balance.

    Resolves ticket 102: a rent-due notice tied to this lease_id. Facilities
    needs monthly_rent and next_due (compared against the shop's "today" in
    the desk table) to judge urgency, and Accounting needs the live
    cash_accounts balance to judge affordability before any payment is
    proposed for human approval. Also reports whether a payment already
    exists for this lease (kind='lease' in the payments table) — a prior
    real payment, not a guess — so a second check after approval doesn't
    mistake "cash is lower now" for "rent still needs to be paid"; it was
    paid out of that very balance. Never invents a lease or balance — if
    the lease id doesn't exist, says so.
    """
    with _connect() as conn:
        lease = conn.execute(
            "SELECT id, space_name, landlord, monthly_rent, next_due, notes FROM leases WHERE id = ?",
            (lease_id,),
        ).fetchone()
        cash = conn.execute("SELECT name, balance, date FROM cash_accounts LIMIT 1").fetchone()
        last_payment = conn.execute(
            """
            SELECT amount, paid_at, approved_by FROM payments
            WHERE kind = 'lease' AND ref_id = ? AND paid_at IS NOT NULL
            ORDER BY paid_at DESC LIMIT 1
            """,
            (lease_id,),
        ).fetchone()
    if lease is None:
        return {"lease_id": lease_id, "found": False, "message": f"No lease found with id {lease_id}."}
    today = _today()
    days_until_due = (date.fromisoformat(lease["next_due"]) - today).days
    balance = cash["balance"] if cash else None
    return {
        "lease_id": lease["id"],
        "found": True,
        "space_name": lease["space_name"],
        "landlord": lease["landlord"],
        "monthly_rent": lease["monthly_rent"],
        "next_due": lease["next_due"],
        "days_until_due": days_until_due,
        "today": today.isoformat(),
        "cash_account": cash["name"] if cash else None,
        "cash_balance": balance,
        "cash_covers_rent": balance is not None and balance >= lease["monthly_rent"],
        "rent_already_paid": last_payment is not None,
        "last_payment_amount": last_payment["amount"] if last_payment else None,
        "last_payment_date": last_payment["paid_at"] if last_payment else None,
        "last_payment_approved_by": last_payment["approved_by"] if last_payment else None,
    }


@mcp.tool
def check_stock_and_restock_options(sku: str, size: str, requested_qty: int) -> dict:
    """Check real stock for a SKU/size against a requested quantity, with restock context.

    Resolves ticket 103: the Yale AI Club wants 20 navy hoodies in size M at
    a bulk discount, but stock may not cover that quantity. Returns the real
    inventory qty and the shortfall (requested_qty - qty, floored at 0), the
    real unit_cost/list_price/margin from pricing so Accounting can judge
    whether a discount is affordable, and the full vendor list (name,
    specialty, lead_days) so the agent team can match a vendor's specialty
    to the product and estimate how fast a shortfall could be restocked.
    Never invents a quantity or price — if the sku/size isn't in inventory,
    says so instead of assuming zero.
    """
    with _connect() as conn:
        stock = conn.execute(
            "SELECT sku, name, size, qty, location FROM inventory WHERE sku = ? AND size = ?",
            (sku, size),
        ).fetchone()
        pricing = conn.execute(
            "SELECT unit_cost, list_price FROM pricing WHERE sku = ?",
            (sku,),
        ).fetchone()
        vendors = conn.execute("SELECT id, name, specialty, lead_days FROM vendors").fetchall()
    if stock is None:
        return {
            "sku": sku,
            "size": size,
            "found": False,
            "message": f"No inventory row found for sku '{sku}' size '{size}'.",
        }
    shortfall = max(0, requested_qty - stock["qty"])
    margin = None
    if pricing is not None:
        margin = round(pricing["list_price"] - pricing["unit_cost"], 2)
    return {
        "sku": stock["sku"],
        "product_name": stock["name"],
        "size": stock["size"],
        "location": stock["location"],
        "found": True,
        "qty_on_hand": stock["qty"],
        "requested_qty": requested_qty,
        "shortfall": shortfall,
        "unit_cost": pricing["unit_cost"] if pricing else None,
        "list_price": pricing["list_price"] if pricing else None,
        "margin_per_unit": margin,
        "vendors": [dict(v) for v in vendors],
    }


@mcp.tool
def list_open_tickets() -> dict:
    """List every ticket currently open on the board.

    This is how the Boss agent sees the whole queue to triage and route
    work, instead of being told ticket ids out of band. Returns every
    column so the caller can decide what to do without a second lookup.
    """
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id, type, requester, subject, sku, size, qty,
                   lease_id, invoice_id, status, notes, created_at
            FROM tickets
            WHERE status = 'open'
            ORDER BY created_at
            """
        ).fetchall()
    return {"count": len(rows), "tickets": [dict(r) for r in rows]}


@mcp.tool
def list_tickets() -> dict:
    """List every ticket on the board, in any status.

    Unlike `list_open_tickets` (which only shows the active queue), this
    is for the dashboard's board view, which needs to show every known
    ticket alongside its current status (open, in_progress,
    needs_approval, or resolved) — not just the ones still open.
    """
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id, type, requester, subject, sku, size, qty,
                   lease_id, invoice_id, status, notes, created_at
            FROM tickets
            ORDER BY id
            """
        ).fetchall()
    return {"count": len(rows), "tickets": [dict(r) for r in rows]}


@mcp.tool
def get_cash_balance() -> dict:
    """Return the shop's current checking balance.

    A plain, single-purpose read of cash_accounts for the dashboard's
    balance display — doesn't require a lease_id like
    get_lease_and_cash_status does.
    """
    with _connect() as conn:
        row = conn.execute("SELECT name, balance, date FROM cash_accounts LIMIT 1").fetchone()
    if row is None:
        return {"found": False, "message": "No cash_accounts row found."}
    return {"found": True, "account": row["name"], "balance": row["balance"], "as_of": row["date"]}


@mcp.tool
def get_ticket(ticket_id: int) -> dict:
    """Look up one ticket's full record by id.

    Agents pass ticket ids to each other when delegating (rather than
    re-describing the whole ticket in prose), so the receiving agent uses
    this tool to pull the authoritative record straight from the tickets
    table. Never invents a ticket — if the id doesn't exist, says so.
    """
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT id, type, requester, subject, sku, size, qty,
                   lease_id, invoice_id, status, notes, created_at
            FROM tickets
            WHERE id = ?
            """,
            (ticket_id,),
        ).fetchone()
    if row is None:
        return {"ticket_id": ticket_id, "found": False, "message": f"No ticket found with id {ticket_id}."}
    return {"found": True, **dict(row)}


_ALLOWED_TICKET_STATUSES = {"open", "in_progress", "needs_approval", "resolved"}


@mcp.tool
def update_ticket(ticket_id: int, status: str, note: str) -> dict:
    """Move a ticket to a new status and append a dated note to its record.

    This is how any agent leaves a trail of what it found or decided on a
    ticket, and how the board reflects real progress. Notes are appended,
    never overwritten, so the full history stays on the ticket. `status`
    must be one of: open, in_progress, needs_approval, resolved — use
    needs_approval for anything a human must sign off on (a payment, a
    price override) rather than marking it resolved prematurely. Never
    invents a ticket — if the id doesn't exist, says so.
    """
    if status not in _ALLOWED_TICKET_STATUSES:
        return {
            "ticket_id": ticket_id,
            "updated": False,
            "message": f"'{status}' is not a valid status. Use one of: {sorted(_ALLOWED_TICKET_STATUSES)}.",
        }
    with _connect() as conn:
        row = conn.execute("SELECT notes FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if row is None:
            return {"ticket_id": ticket_id, "updated": False, "message": f"No ticket found with id {ticket_id}."}
        today = _today()
        existing = (row["notes"] or "").strip()
        stamped = f"[{today.isoformat()}] {note}"
        new_notes = f"{existing}\n{stamped}" if existing else stamped
        conn.execute("UPDATE tickets SET status = ?, notes = ? WHERE id = ?", (status, new_notes, ticket_id))
        conn.commit()
    return {"ticket_id": ticket_id, "updated": True, "status": status, "notes": new_notes}


@mcp.tool
def make_payment(kind: str, ref_id: int, amount: float, account: str, approved_by: str) -> dict:
    """Actually move shop cash to pay a vendor invoice or a lease's rent.

    This is the only tool that moves real money, so it is wired on the
    agent side to require human approval before it can run — an agent
    attempting this call will have it deferred for a human to approve,
    never executed silently. `kind` must be "invoice" (ref_id = an
    invoices.id — on success the invoice's status flips to "paid", which
    is what unblocks that vendor from shipping again) or "lease" (ref_id =
    a leases.id, a straightforward rent payment). Refuses and makes no
    change at all if the payment would take cash_accounts.balance below
    zero — this shop never goes into a negative balance. `approved_by`
    must name the human who approved it; it is recorded on the payment
    row and is never filled in by an agent.
    """
    if kind not in {"invoice", "lease"}:
        return {"paid": False, "message": f"'{kind}' is not a valid kind. Use 'invoice' or 'lease'."}
    with _connect() as conn:
        if kind == "invoice":
            ref = conn.execute("SELECT id, status FROM invoices WHERE id = ?", (ref_id,)).fetchone()
        else:
            ref = conn.execute("SELECT id FROM leases WHERE id = ?", (ref_id,)).fetchone()
        if ref is None:
            return {"paid": False, "message": f"No {kind} found with id {ref_id}."}
        cash = conn.execute("SELECT name, balance FROM cash_accounts LIMIT 1").fetchone()
        if cash is None:
            return {"paid": False, "message": "No cash_accounts row found."}
        if cash["balance"] < amount:
            return {
                "paid": False,
                "message": (
                    f"Refused: paying {amount} from '{cash['name']}' (balance {cash['balance']}) "
                    "would go negative. No change made."
                ),
            }
        today = _today()
        cur = conn.execute(
            "INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by) VALUES (?, ?, ?, ?, ?, ?)",
            (kind, ref_id, amount, account, today.isoformat(), approved_by),
        )
        payment_id = cur.lastrowid
        new_balance = cash["balance"] - amount
        conn.execute(
            "UPDATE cash_accounts SET balance = ?, date = ? WHERE name = ?",
            (new_balance, today.isoformat(), cash["name"]),
        )
        if kind == "invoice":
            conn.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (ref_id,))
        conn.commit()
    return {
        "paid": True,
        "payment_id": payment_id,
        "kind": kind,
        "ref_id": ref_id,
        "amount": amount,
        "account": account,
        "approved_by": approved_by,
        "paid_at": today.isoformat(),
        "new_cash_balance": new_balance,
        "invoice_marked_paid": kind == "invoice",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Campus Customs operations MCP server")
    parser.add_argument(
        "--http",
        action="store_true",
        help="Serve Streamable HTTP on port 8002 (keeps FastAPI free on 8000)",
    )
    args = parser.parse_args()
    if args.http:
        mcp.run(transport="http", host="127.0.0.1", port=8002)
    else:
        mcp.run()
