# Dashboard Design

## Concept: a warm study desk, not a dashboard

Instead of a typical dark-mode ops dashboard, the board is framed as a librarian's study desk: a walnut-paneled room, a leather desk blotter, a wooden tray of paper ticket slips, a green ledger pad for the live feed, cream index cards for agent summaries, and a brass plaque for the cash balance. The goal was a space a Yale/New Haven shopkeeper would actually want to sit at, not a generic admin panel — "serious tool" and "warm, specific place" aren't mutually exclusive, and the second one is more memorable.

- **Background** — a subtle diagonal wood-grain stripe (`repeating-linear-gradient`) in walnut tones, giving texture without competing with the content.
- **Header** — near-black walnut bar with a brass bottom border and a brass "CC" crest, like a brass nameplate on a study door.
- **Typography** — Fraunces (a warm serif) for every heading, so the board reads like a ledger/plaque rather than a web app; Inter for body text so it stays legible at small sizes. A cursive accent (Caveat) is used once, for the approval slip's "Pay to the Order Of" stamp.
- **Color** — walnut/brass/leather/ledger-green carries the "study" feel; Yale blue and gold are kept as the accent layer (the Boss's navy nameplate, gold status badges, gold "ring the bell" button, gold ticket-eyebrow text) so the project's blue/gold/silver convention isn't abandoned, just reinterpreted as brass-and-navy accents on a wood base rather than a literal blue/gold background.

## How agents read differently

Each of the five agents has its own color and initials "nameplate" (a small circle badge), used consistently in the live event feed and the summary cards — Handsome Dan (Boss) in navy, Sterling (Inventory) in a library-brown, Ledger (Accounting) in forest green, Harkness (Facilities) in stone gray, Clark (Customer Service) in a warm red. This means a human scanning the feed can tell who's talking at a glance, without reading every line — the same trick a real transcript or group chat uses with avatar colors.

The event feed itself (`EventFeed.tsx`) is styled like a bookkeeper's ledger pad: faint ruled lines, each row showing the agent's nameplate, name+role, a timestamp, which tool it called, and what came back. A row where a tool call is waiting on human approval gets a soft gold highlight and an explicit "— awaiting human approval" flag, so the one moment that actually matters (a deferred payment) doesn't get lost in the scroll.

Agent summaries (`AgentSummaries.tsx`) are rendered as a grid of index cards — lightly rotated, lined paper, a colored top border matching that agent's nameplate color — pulling each agent's own natural-language summary (reconstructed from the real `delegate` tool results already in the audit trail, not a separate API) into small, scannable blurbs rather than making a human read the full raw event log to understand what happened.

## How resolved tickets and cash show up

Ticket status is a real, honest reflection of what the backend's own data says — not a cosmetic "done" flag. The board distinguishes three things that are easy to conflate: a ticket's **persisted status** (open / in progress / needs approval / resolved, shown as a static colored badge in the tray), whether it is **currently executing** (a separate pulsing "Agents Working…" badge, shown only while a run is in flight), and whether a human still needs to **act** (the "Human Decision Needed" / "Approve a Payment" panel on the desk itself). Keeping these three separate matters: in live testing, ticket 101 genuinely moved from `needs_approval` to `in_progress` (not `resolved`) after its invoice was paid, because the agents correctly recognized the physical tee was still out of stock — a real, nuanced distinction the UI needed to be able to show without over-claiming "resolved."

The cash balance is a brass plaque in the header, visible from everywhere on the board (not buried in a ticket), and briefly flashes red-to-gold when a real approval drops the balance — a small, honest piece of feedback that a payment actually happened, confirmed live across two real approvals in testing ($3,400 → $2,560 → $160).

## The two creative choices that make it feel special

1. **"Ring for the Team"** instead of a plain "Run" button — a brass bell button that visually reads as calling a concierge desk, tying the agent-run action to the physical "desk" metaphor instead of a generic app verb.
2. **The approval slip reads like an actual check** — a dashed-border card with a handwritten-style "Pay to the Order Of" stamp and an underline-style form (no boxed inputs), and it only appears in its full payment form when there's a real invoice/lease to pay (pre-filled from the real tool results already in that ticket's event feed, never hardcoded) — a ticket that just needs a policy judgment call (like the bulk-discount override) gets an honest "Human Decision Needed" note instead of a payment form with nothing to fill in.

## Why these choices should help Campus Customs

A shop that's visibly staffed by named, color-coded "employees" who show their work (not a black-box "AI did something") reads as more trustworthy to whoever's reviewing it — a human approving real payments wants to see the reasoning, not just a result. The desk/ledger/study framing also doubles as a quiet piece of Yale/New Haven branding: it feels like it belongs to the same world as yalebulldogblue.com and the physical Chapel Street shop, not like a generic SaaS admin tool bolted onto the business.
