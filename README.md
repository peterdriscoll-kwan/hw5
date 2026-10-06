# Campus Customs — Multi-Agent Operations (Homework 5)

A multi-agent ops team for the Campus Customs shop: an MCP server exposing the
real shop database, a PydanticAI agent team (Boss, Inventory, Accounting,
Facilities, Customer Service) behind FastAPI, and a React + Vite + TypeScript
dashboard for a human to watch the agents work and approve real payments.

Full technical reference (database tables, all MCP tools, the five agents,
every API route, the dashboard, and the safety rules) is in
[`output/harness.md`](output/harness.md). The full prompt-by-prompt build log
is in [`AI_prompts.md`](AI_prompts.md).

## Prerequisites

- Python 3.11+
- Node 18+
- A [Portkey](https://portkey.ai) API key with access to the `gpt-6-luna`
  model (this project uses **only** `gpt-6-luna` — no other model is called
  anywhere in this codebase)

## Setup

```bash
# from this folder (hw5/)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# then edit .env and set your real PORTKEY_API_KEY

cd frontend
npm install
cd ..
```

## Resetting the database before a clean run

`data/campus_customs.db` is the original seed and is never written to.
`data/campus_customs_new.db` is the working copy every tool actually reads
and writes. Before a full three-ticket run (all three tickets `open`,
checking balance `$3,400.00`), reset the working copy from the original:

```bash
cp data/campus_customs.db data/campus_customs_new.db
```

(The running backend also exposes this as `POST /api/reset`.)

## Running the app

Three pieces, each in its own terminal, from this folder:

**1. MCP server** (optional to run standalone — the backend below also
spawns this automatically as a subprocess; running it by hand is useful
for testing the tools directly, e.g. via Claude Code's `.mcp.json` in this
repo):

```bash
cd mcp_server
python server.py
```

**2. FastAPI backend** (the agent team lives here):

```bash
cd backend
uvicorn main:app --reload --port 8000
```

**3. React dashboard**:

```bash
cd frontend
npm run dev
```

Open the printed `http://localhost:5173` URL. The dashboard lists the three
tickets, lets you "Ring for the Team" to run the agents on one, shows a live
per-agent event feed, lets a human approve a real payment when one is
proposed, and shows the live checking balance.

## What's already been run

`output/resolved_tickets.json`, `output/resolved_board.html`, and
`output/desk_tickets.html` document a complete run where all three seed
tickets were worked end-to-end to a genuine `resolved` status (starting
balance `$3,400.00` → ending balance `$160.00`). `data/campus_customs_new.db`
is currently left in that resolved end-state — reset it (above) if you want
to watch a fresh run yourself.
