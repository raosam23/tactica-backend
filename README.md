<div align="center">

# 🏟️ Tactica

### A sports-only AI pundit, powered by RAG and a multi-agent debate pipeline

<p>
  <img alt="Python"    src="https://img.shields.io/badge/Python-3.12%2B-3776AB?style=flat-square&logo=python&logoColor=white" />
  <img alt="FastAPI"   src="https://img.shields.io/badge/FastAPI-Async-009688?style=flat-square&logo=fastapi&logoColor=white" />
  <img alt="Postgres"  src="https://img.shields.io/badge/PostgreSQL-Neon-4169E1?style=flat-square&logo=postgresql&logoColor=white" />
  <img alt="pgvector"  src="https://img.shields.io/badge/pgvector-VECTOR(1536)-6E40C9?style=flat-square" />
  <img alt="OpenAI"    src="https://img.shields.io/badge/OpenAI-gpt--4o--mini-111111?style=flat-square&logo=openai&logoColor=white" />
  <img alt="AutoGen"   src="https://img.shields.io/badge/AutoGen-AgentChat-FF6B35?style=flat-square" />
  <img alt="Status"    src="https://img.shields.io/badge/status-backend--complete-success?style=flat-square" />
</p>

<sub>Backend repository · Frontend not yet started</sub>

</div>

---

## 📖 Table of Contents

- [What is Tactica?](#-what-is-tactica)
- [How it works](#-how-it-works)
- [Architecture at a glance](#-architecture-at-a-glance)
- [Tech stack](#-tech-stack)
- [Project layout](#-project-layout)
- [Database schema](#-database-schema)
- [Getting started](#-getting-started)
- [Environment variables](#-environment-variables)
- [API reference](#-api-reference)
- [Agent pipeline](#-agent-pipeline)
- [Agent tools](#-agent-tools)
- [Roadmap](#-roadmap)

---

## 🧠 What is Tactica?

Tactica is the **backend** of a 1-on-1 sports chatbot. A logged-in user opens a conversation and talks to an AI **pundit** that can take a stance, debate, share stats and tell stories — but **only about sports**.

What makes it different from a plain LLM chat:

- **Retrieval-augmented.** Answers are grounded in real documents stored as embeddings in PostgreSQL via `pgvector`.
- **Live ingestion.** When the knowledge base doesn't know about a topic, the agent can **scrape Wikipedia / RSS, chunk, embed and store** it on the fly — then answer using fresh evidence.
- **Multi-agent debate.** Behind a single "pundit" persona, four specialist AutoGen agents (Stats, Storyteller, Debater, Moderator) collaborate before the user sees one polished answer.
- **Conversation-scoped memory.** A separate `conversation_memory` vector table remembers facts, opinions and conclusions per chat thread.
- **Sports-only.** A guardrail agent rejects non-sports prompts before any heavy work is done.

> ⚠️ **Frontend status:** This repo is backend-only. A Next.js frontend is planned but not yet started.

---

## 🔁 How it works

When a user sends a message to `POST /api/conversations/{id}/chat`, this is what happens behind the scenes:

```
                ┌──────────────────────────┐
   user msg →   │  GuardrailAgent          │  → "NOT_SPORTS" → polite refusal
                └────────────┬─────────────┘
                             ▼ "SPORTS"
                ┌──────────────────────────┐
                │  SportDetectorAgent      │  → e.g. "football", "tennis", "general"
                └────────────┬─────────────┘
                             ▼
            persist user msg, load last 10 messages as context
                             ▼
   ┌─────────────────────────────────────────────────────────┐
   │              SelectorGroupChat (AutoGen)                │
   │                                                         │
   │   StatsPundit   StorytellerPundit   DebaterPundit       │
   │        \              |                   /             │
   │         └──────► ModeratorPundit ◄───────┘              │
   │                  (says TERMINATE)                       │
   └─────────────────────────────┬───────────────────────────┘
                                 ▼
              persist assistant msg + citations
                                 ▼
              MemoryWriter → conversation_memory
                                 ▼
              TitleAgent (only on first turn)
                                 ▼
                       return final answer
```

**Termination:** the team stops when `ModeratorPundit` ends its message with `TERMINATE`, or after 20 messages.

---

## 🏗️ Architecture at a glance

```
        ┌────────────────────────┐
client → │   FastAPI (Uvicorn)    │
        └──────────┬─────────────┘
                   │
        ┌──────────┴─────────────┐
        │   /api/auth            │  JWT register / login / delete-me
        │   /api/conversations   │  CRUD + /chat (the pipeline)
        │   /api/conversations/  │  /messages list
        │      {id}/messages     │
        └──────────┬─────────────┘
                   │
        ┌──────────┴─────────────┐
        │  Services layer        │  auth · conversation · message · rag · ingestion
        └──────────┬─────────────┘
                   │
        ┌──────────┴─────────────┐
        │  Agents layer          │  pipeline · agents · tools · group_chat
        └──────────┬─────────────┘
                   │
   ┌───────────────┴───────────────┐
   │   PostgreSQL + pgvector       │   user, conversation, message,
   │   (NeonDB compatible)         │   message_citations, document,
   │                               │   conversation_memory
   └───────────────────────────────┘
```

---

## 🧰 Tech stack

| Layer                  | Choice                                        |
| ---------------------- | --------------------------------------------- |
| Language               | Python 3.12+                                  |
| API framework          | FastAPI (async)                               |
| Server                 | Uvicorn                                       |
| ORM / models           | SQLModel + SQLAlchemy async                   |
| DB                     | PostgreSQL (Neon-compatible, SSL required)    |
| Vector search          | `pgvector` (cosine distance, dim = 1536)      |
| Migrations             | Alembic (async env)                           |
| Auth                   | JWT (`python-jose`) + `bcrypt` password hash  |
| LLM provider           | OpenAI (`gpt-4o-mini` by default)             |
| Embeddings             | OpenAI `text-embedding-3-small`               |
| Multi-agent framework  | Microsoft **AutoGen AgentChat**               |
| Web ingestion          | Wikipedia API, RSS via `feedparser`, `httpx`  |
| Package manager        | `uv`                                          |

---

## 📁 Project layout

```
backend/
├── app/
│   ├── main.py                     # FastAPI app + CORS + /health
│   ├── core/config.py              # Pydantic settings (.env loader)
│   ├── db/database.py              # async engine + session factory
│   │
│   ├── api/
│   │   ├── router.py               # mounts /api with auth, conversations, messages
│   │   └── routes/
│   │       ├── auth.py             # /api/auth/{register,login,me}
│   │       ├── conversations.py    # /api/conversations + /chat
│   │       └── messages.py         # /api/conversations/{id}/messages
│   │
│   ├── models/                     # SQLModel tables
│   │   ├── user.py
│   │   ├── conversation.py
│   │   ├── message.py
│   │   ├── message_citation.py
│   │   ├── document.py
│   │   └── conversation_memory.py
│   │
│   ├── schemas/                    # Pydantic request/response DTOs
│   │   ├── auth.py
│   │   ├── conversation.py
│   │   └── message.py
│   │
│   ├── services/                   # business logic
│   │   ├── authentication_service.py
│   │   ├── conversation_service.py
│   │   ├── message_service.py
│   │   ├── rag_service.py          # pgvector cosine search + memory writes
│   │   ├── ingestion_service.py    # scrape → chunk → embed → store
│   │   ├── scraper_service.py      # Wikipedia + RSS
│   │   ├── chunker_service.py      # character chunking with overlap
│   │   └── embedding_service.py    # OpenAI embedding calls
│   │
│   ├── agents/                     # AutoGen layer
│   │   ├── model_client.py         # OpenAIChatCompletionClient factory
│   │   ├── agents.py               # all AssistantAgent definitions + prompts
│   │   ├── tools.py                # FunctionTool implementations (RAG-backed)
│   │   ├── group_chat.py           # SelectorGroupChat for the pundit team
│   │   └── pipeline.py             # the orchestrator called by /chat
│   │
│   └── utils/security.py           # JWT, bcrypt, get_current_user dependency
│
├── alembic/                        # migration env + 4 revisions
├── alembic.ini
├── pyproject.toml                  # deps managed by uv
└── uv.lock
```

---

## 🗄️ Database schema

Six tables, all migrated via Alembic:

| Table                 | Purpose                                                                           |
| --------------------- | --------------------------------------------------------------------------------- |
| `user`                | Accounts — email, bcrypt password hash, optional name                             |
| `conversation`        | Chat threads, scoped to a user                                                    |
| `message`             | Every user / assistant turn (`role` enum)                                         |
| `message_citations`   | Many-to-many between assistant messages and the documents that informed them, with `relevance_score` |
| `document`            | **Global RAG store** — text chunks + `VECTOR(1536)` embedding + sport tag + JSONB metadata |
| `conversation_memory` | **Per-conversation memory** — extracted facts/opinions, embedded for vector lookup |

Foreign keys use `ON DELETE CASCADE`, so deleting a conversation cleans up its messages and memory automatically.

---

## 🚀 Getting started

### 1. Prerequisites

- Python **3.12+**
- [`uv`](https://docs.astral.sh/uv/) — `pipx install uv` or follow the official installer
- A PostgreSQL database with the `vector` extension available (Neon works out of the box; the connection requires SSL)
- An OpenAI API key

### 2. Install

```bash
git clone <this-repo>
cd backend
uv sync
```

### 3. Configure

Create a `.env` in the `backend/` directory — see [Environment variables](#-environment-variables) below.

### 4. Run migrations

```bash
uv run alembic upgrade head
```

This creates all six tables and enables the `pgvector` extension.

### 5. Start the server

```bash
uv run uvicorn app.main:app --reload
```

| Surface         | URL                              |
| --------------- | -------------------------------- |
| Health check    | `http://127.0.0.1:8000/health`   |
| Swagger UI      | `http://127.0.0.1:8000/docs`     |
| ReDoc           | `http://127.0.0.1:8000/redoc`    |

---

## ⚙️ Environment variables

Loaded from `.env` via `pydantic-settings`.

| Variable                      | Required | Default                                                | Notes                                          |
| ----------------------------- | :------: | ------------------------------------------------------ | ---------------------------------------------- |
| `APP_NAME`                    |          | `Tactica`                                              |                                                |
| `APP_ENV`                     |          | `development`                                          |                                                |
| `DEBUG`                       |          | `True`                                                 | Enables SQLAlchemy `echo`                      |
| `DATABASE_URL`                |    ✅    | —                                                      | Must be `postgresql+asyncpg://...`             |
| `SECRET_KEY`                  |    ✅    | —                                                      | JWT signing secret                             |
| `ALGORITHM`                   |          | `HS256`                                                |                                                |
| `ACCESS_TOKEN_EXPIRE_MINUTES` |          | `30`                                                   |                                                |
| `SALT_ROUNDS`                 |          | `12`                                                   | bcrypt cost                                    |
| `OPENAI_API_KEY`              |    ✅    | —                                                      |                                                |
| `OPENAI_MODEL`                |          | `gpt-4o-mini`                                          | Used by every agent                            |
| `EMBEDDING_MODEL`             |          | `text-embedding-3-small`                               |                                                |
| `VECTOR_DIMENSION`            |          | `1536`                                                 | Must match the embedding model                 |
| `ALLOWED_ORIGINS`             |          | `["http://localhost:3000", "http://localhost:8000"]`   | CORS allowlist                                 |

### Example `.env`

```env
APP_NAME=Tactica
APP_ENV=development
DEBUG=true

DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST:5432/DB_NAME

SECRET_KEY=replace-me-with-something-long-and-random
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
SALT_ROUNDS=12

OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
VECTOR_DIMENSION=1536
```

> The async engine is created with `connect_args={"ssl": "require"}`. Use a Postgres host that accepts SSL (Neon, Supabase, RDS, etc.).

---

## 🌐 API reference

All routes are mounted under the `/api` prefix. Every protected route expects:

```http
Authorization: Bearer <jwt>
```

### Route map

| Method | Path                                              | Auth | Purpose                                       |
| :----: | ------------------------------------------------- | :--: | --------------------------------------------- |
|  GET   | `/health`                                         |  ❌  | Liveness probe                                |
|  POST  | `/api/auth/register`                              |  ❌  | Create user, return JWT                       |
|  POST  | `/api/auth/login`                                 |  ❌  | Verify credentials, return JWT                |
| DELETE | `/api/auth/me`                                    |  ✅  | Delete the current user's account             |
|  POST  | `/api/conversations/`                             |  ✅  | Create a new conversation                     |
|  GET   | `/api/conversations/`                             |  ✅  | List the current user's conversations         |
|  GET   | `/api/conversations/{conversation_id}`            |  ✅  | Fetch a single conversation                   |
| DELETE | `/api/conversations/{conversation_id}`            |  ✅  | Delete a conversation (cascades messages)     |
|  POST  | `/api/conversations/{conversation_id}/chat`       |  ✅  | **Run the full multi-agent pipeline**         |
|  GET   | `/api/conversations/{conversation_id}/messages`   |  ✅  | List all messages in a conversation           |

<details>
<summary><strong>POST /api/auth/register</strong> — 201 Created</summary>

Request:
```json
{ "email": "user@example.com", "password": "strong-password", "name": "Samarth" }
```
Response:
```json
{ "access_token": "<jwt>", "token_type": "bearer" }
```
</details>

<details>
<summary><strong>POST /api/auth/login</strong> — 200 OK</summary>

Request:
```json
{ "email": "user@example.com", "password": "strong-password" }
```
Response:
```json
{ "access_token": "<jwt>", "token_type": "bearer" }
```
</details>

<details>
<summary><strong>DELETE /api/auth/me</strong> — 200 OK</summary>

Response:
```json
{ "id": "uuid", "email": "user@example.com", "name": "Samarth" }
```
</details>

<details>
<summary><strong>POST /api/conversations/</strong> — 201 Created</summary>

Request (title is optional — if omitted, the `TitleAgent` will generate one after the first chat turn):
```json
{ "title": "Champions League Debate" }
```
Response:
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "title": "Champions League Debate",
  "created_at": "2026-05-05T10:00:00Z",
  "updated_at": "2026-05-05T10:00:00Z"
}
```
</details>

<details>
<summary><strong>GET /api/conversations/</strong> — 200 OK</summary>

Response: an array of `ConversationResponse` objects.
</details>

<details>
<summary><strong>GET /api/conversations/{conversation_id}</strong> — 200 OK</summary>

Response: a single `ConversationResponse`. Returns 404 if the conversation does not belong to the caller.
</details>

<details>
<summary><strong>DELETE /api/conversations/{conversation_id}</strong> — 200 OK</summary>

Returns the deleted conversation. Cascades through `message`, `message_citations`, and `conversation_memory`.
</details>

<details>
<summary><strong>POST /api/conversations/{conversation_id}/chat</strong> — 200 OK</summary>

Request:
```json
{ "message": "Was Barcelona's 2011 team better than Manchester City's treble side?" }
```
Response:
```json
{ "message": "<final pundit answer>" }
```

What this endpoint actually does:

1. Verifies the conversation belongs to the caller.
2. Runs the **GuardrailAgent**. If the prompt is not sports-related, returns a polite refusal immediately.
3. Runs the **SportDetectorAgent** to tag the query (e.g. `football`, `tennis`, or `general`).
4. Loads the last 10 messages as context.
5. Persists the user message.
6. Spins up the four pundit agents and runs a **`SelectorGroupChat`** until `ModeratorPundit` says `TERMINATE` (or 20 messages elapse).
7. Persists the assistant's final reply, plus citations into `message_citations`.
8. Runs the **MemoryWriter** agent over the exchange to extract durable facts into `conversation_memory`.
9. If the conversation has no title yet, runs the **TitleAgent**.
</details>

<details>
<summary><strong>GET /api/conversations/{conversation_id}/messages</strong> — 200 OK</summary>

Response:
```json
[
  {
    "id": "uuid",
    "conversation_id": "uuid",
    "role": "user",
    "content": "...",
    "created_at": "2026-05-05T10:01:00Z"
  },
  {
    "id": "uuid",
    "conversation_id": "uuid",
    "role": "assistant",
    "content": "...",
    "created_at": "2026-05-05T10:01:05Z"
  }
]
```
</details>

### Quick `curl` walkthrough

```bash
# 1. Register and capture the token
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"u@x.com","password":"hunter22","name":"Samarth"}' \
  | jq -r '.access_token')

# 2. Create a conversation
CID=$(curl -s -X POST http://127.0.0.1:8000/api/conversations/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}' | jq -r '.id')

# 3. Talk to the pundit
curl -X POST "http://127.0.0.1:8000/api/conversations/$CID/chat" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"Who had the greater peak — Messi or Maradona?"}'

# 4. Read the thread
curl "http://127.0.0.1:8000/api/conversations/$CID/messages" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 🤖 Agent pipeline

All agents are `autogen_agentchat.agents.AssistantAgent` instances backed by the same `OpenAIChatCompletionClient`. They are split into two layers:

### Pre-pipeline agents (cheap, no tools)

| Agent                  | Job                                                                      |
| ---------------------- | ------------------------------------------------------------------------ |
| **GuardrailAgent**     | Replies with exactly `SPORTS` or `NOT_SPORTS`. Filters out off-topic chat |
| **SportDetectorAgent** | Returns the lowercase sport name, or `general` if it can't decide        |

### Pundit team (`SelectorGroupChat`)

| Agent                  | Job                                                                            |
| ---------------------- | ------------------------------------------------------------------------------ |
| **StatsPundit**        | Pulls precise statistics, comparisons and records                              |
| **StorytellerPundit**  | Adds narrative, history, career arcs and historical parallels                  |
| **DebaterPundit**      | Fact-checks claims and surfaces opposing viewpoints                            |
| **ModeratorPundit**    | Synthesizes everything into a single opinionated answer; ends with `TERMINATE` |

### Side-effect agents

| Agent             | Job                                                                                |
| ----------------- | ---------------------------------------------------------------------------------- |
| **MemoryWriter**  | Reads the user/assistant exchange and writes useful facts into `conversation_memory` |
| **TitleAgent**    | Generates a ≤6-word title for the conversation if it doesn't have one yet            |

---

## 🛠️ Agent tools

All tools are `FunctionTool` wrappers around async Python functions in `app/agents/tools.py`. Each one is a thin wrapper over the RAG / ingestion services.

| Tool                       | Used by              | What it does                                                                       |
| -------------------------- | -------------------- | ---------------------------------------------------------------------------------- |
| `search_stats`             | StatsPundit          | Cosine similarity over `document`, returns top-k snippets + sources                |
| `compare_players`          | StatsPundit          | Runs `search_stats` for each player and groups results                             |
| `search_articles`          | StorytellerPundit    | Same vector search, framed for narrative content                                   |
| `get_historical_parallel`  | StorytellerPundit    | Vector search aimed at finding analogous past events                               |
| `fact_check`               | DebaterPundit        | Vector search for evidence supporting/contradicting a claim                        |
| `search_opposing_view`     | DebaterPundit        | Vector search aimed at counter-perspectives                                        |
| `search_memory`            | All pundits          | Cosine similarity over `conversation_memory` (scoped to this conversation)         |
| `ingest_and_search`        | All pundits          | Live Wikipedia ingestion → chunk → embed → store, then `search_stats`              |
| `add_memory`               | MemoryWriter         | Embeds and writes a fact into `conversation_memory`                                |

Whenever a search tool returns a hit, the document's `(id, score)` is recorded in a per-request `cited_documents` list. After the moderator finishes, those citations are persisted into `message_citations`.

---

## 🗺️ Roadmap

The backend is functional end-to-end. Known follow-ups:

### 🐞 Bug — `GuardrailAgent` is too strict

The current `GuardrailAgent` decides `SPORTS` vs `NOT_SPORTS` purely from the LLM's training data, so it rejects prompts about lesser-known or recent athletes (e.g. **Vaibhav Suryavanshi**) on the assumption they're nonsense.

**Plan:** loosen the guardrail's system prompt so that any prompt with a *reasonable chance* of being sports-related passes through. False positives downstream are cheaper than blocking real sports questions.

### 🐞 Bug — Agents skip `ingest_and_search`

The pundit agents default to searching the existing `document` table and stop there, even when the topic is something the knowledge base has never seen (current events, ongoing seasons, recent matches, unknown players/teams).

**Plan:** update the `StatsPundit` / `StorytellerPundit` / `DebaterPundit` system prompts to **explicitly require** calling `ingest_and_search` *first* whenever the question involves:
- current events or ongoing seasons
- recent matches or transfers
- players / teams the agent isn't confident about

…and only then fall back to the cheaper `search_*` tools.

### ✨ Feature — `GeneralistPundit` agent

Not every sports question needs stats, narrative, or debate. Casual prompts ("who's playing tonight?", "what's offside?") currently get force-routed through the full retrieval-heavy pipeline.

**Plan:** add a `GeneralistPundit` to the `SelectorGroupChat` participants list. It carries **no tools** and answers from its own LLM knowledge. The `SelectorGroupChat`'s selector should route to it when the question doesn't strictly require Stats / Storyteller / Debater work, leaving the heavy specialists for questions that actually warrant them.

### Other follow-ups

- **Return citations in the chat response.** They are already persisted in `message_citations` — the API just doesn't surface them yet.
- **Frontend.** Build the Next.js client.
- **Richer ingestion.** More sources beyond Wikipedia + RSS; an internal admin endpoint to trigger ingestion explicitly.
- **Observability.** Per-turn traces for retrieval quality, tool calls, and agent decisions.

---

<div align="center">
  <sub>Built for sports conversations that feel <b>opinionated, informed, and context-aware</b>.</sub>
</div>
