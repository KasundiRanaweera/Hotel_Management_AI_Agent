# Hotel Management AI Agent

A chat-based AI assistant for a hotel front desk. Staff type natural-language
requests — e.g. *"Register a new guest, Jane Smith, room 204"* — and the agent
collects the right details, then adds, views, updates, or deletes the
customer's record using tool/function calling, backed by a local SQLite
database.

This project was built as a student assignment to demonstrate an AI agent
that uses tools to work with stored data, asks for missing information
instead of guessing, and protects data from accidental loss.

## Tech stack

- **Python** — core language
- **Jupyter Notebook** — single-notebook implementation (`hotel_agent.ipynb`)
- **OpenAI Python library** — used as the client for tool/function calling
- **Model provider** — switchable via one variable (`PROVIDER` in the config
  cell):
  - `"ollama"` → local **llama3.1:8b**, served through [Ollama](https://ollama.com)
  - `"groq"` → **openai/gpt-oss-120b** via the [Groq](https://groq.com) API
- **SQLite** — local, file-based persistent storage (`hotel.db`)
- **Gradio** — chat interface (`ChatInterface`)
- **uv** — Python environment and dependency management

## Project structure

```
hotel-ai-agent/
├── hotel_agent.ipynb      # the entire project: db, tools, agent, chat UI
├── hotel.db                # created automatically on first run (not committed)
├── demo/                   # screenshots demonstrating each requirement
├── pyproject.toml          # uv project config
├── uv.lock                 # locked dependency versions
├── requirement.txt         # plain pip-installable export of the lockfile
├── .env                     # local secrets (not committed — see Setup)
└── README.md
```

## Setup

1. Install [uv](https://docs.astral.sh/uv/).
2. Clone or download this repository and open a terminal in the project folder.
3. Install dependencies:
   ```bash
   uv sync
   ```
4. Choose a model provider:
   - **Local (recommended, no API key needed):**
     ```bash
     ollama pull llama3.1:8b
     ollama serve
     ```
     Leave `PROVIDER = "ollama"` in the notebook's config cell.
   - **Cloud (Groq):** create a `.env` file in the project root containing:
     ```
     GROQ_API_KEY=your_key_here
     ```
     Set `PROVIDER = "groq"` in the notebook's config cell.
5. Open `hotel_agent.ipynb` (e.g. `uv run jupyter notebook`) and run every
   cell from top to bottom. A Gradio chat window will open in your browser.

## Functional requirements covered

| Requirement | Status |
|---|---|
| FR1 — Ask for missing details conversationally, never guess | ✅ |
| FR2 — Save with auto-generated unique ID + confirmation | ✅ |
| FR3 — View by ID or name; handle no-match and multiple-match cases | ✅ |
| FR4 — Update one or more fields; customer ID is immutable | ✅ |
| FR5 — Explicit yes/no confirmation required before delete | ✅ |
| FR6 — Reject invalid data with a plain-language explanation | ✅ |
| FR7 — Records persist after restarting the program | ✅ |
| FR8 — Never claims success unless the action really succeeded | ✅ |
| FR9 — Politely redirects off-topic requests (Should-have) | ✅ |

## Data validated per the brief

- **Full name** — required, cannot be empty
- **Phone** — required, 9–15 digits, optional leading `+`
- **Email** — optional, validated as a plausible address if given
- **Room number** — required, free text (e.g. `101`, `A12`)
- **Check-in / check-out** — required, `YYYY-MM-DD`; check-out must be after check-in
- **Special requests** — optional, free text

## Design notes

- Delete confirmation is enforced in Python (not left purely to the model's
  judgment) using a pending-delete state, so a "yes" is always required
  before `delete_customer` actually runs — this makes FR5 reliable even with
  a smaller local model.
- Conversation history passed into the agent strips Gradio's internal message
  formatting down to plain role/content pairs before being sent to the model,
  keeping the context clean across turns.

## Demo

The `demo/` folder contains screenshots covering:
- Registering a new guest (step-by-step detail collection)
- Viewing by ID, by name (single and multiple matches), and a not-found case
- Updating a field and confirming the customer ID can't be changed
- A rejected invalid phone number and an invalid date range
- A confirmed delete and a cancelled delete
- Off-topic requests being politely redirected
- A persistence check after restarting the kernel

## Out of scope (per assignment brief)

Online payments or billing, room availability/pricing, staff logins, and a
full website or mobile app are explicitly excluded.

## Possible extensions (bonus ideas)

- List all customers
- Search by check-in date
- Export the customer list as a PDF
- Smarter handling of duplicate names
