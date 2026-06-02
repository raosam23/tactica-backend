<div align="center">

# Tactica — Backend

### A sports-only AI pundit, powered by RAG and a multi-agent debate pipeline

<p>
  <img alt="Python"    src="https://img.shields.io/badge/Python-3.12%2B-3776AB?style=flat-square&logo=python&logoColor=white" />
  <img alt="FastAPI"   src="https://img.shields.io/badge/FastAPI-Async-009688?style=flat-square&logo=fastapi&logoColor=white" />
  <img alt="Postgres"  src="https://img.shields.io/badge/PostgreSQL-Neon-4169E1?style=flat-square&logo=postgresql&logoColor=white" />
  <img alt="pgvector"  src="https://img.shields.io/badge/pgvector-VECTOR(1536)-6E40C9?style=flat-square" />
  <img alt="OpenAI"    src="https://img.shields.io/badge/OpenAI-gpt--4o--mini-111111?style=flat-square&logo=openai&logoColor=white" />
  <img alt="AutoGen"   src="https://img.shields.io/badge/AutoGen-AgentChat-FF6B35?style=flat-square" />
  <img alt="Status"    src="https://img.shields.io/badge/status-complete-success?style=flat-square" />
</p>

<sub>Backend repository · <a href="https://github.com/raosam23/tactica-frontend">Frontend repository →</a></sub>

</div>

---

## Table of Contents

- [What is Tactica?](#what-is-tactica)
- [How it works](#how-it-works)
- [Architecture](#architecture)
- [Tech stack](#tech-stack)
- [Project layout](#project-layout)
- [Database schema](#database-schema)
- [Getting started](#getting-started)
- [Environment variables](#environment-variables)
- [API reference](#api-reference)
- [Agent pipeline](#agent-pipeline)
- [Agent tools](#agent-tools)
- [Roadmap](#roadmap)

---

## What is Tactica?

Tactica is the **backend** of a 1-on-1 sports chatbot. A logged-in user opens a conversation and talks to an AI **pundit** that can take a stance, debate, share stats and tell stories — but **only about sports**. The final answer is **streamed back token by token** over Server-Sent Events.

What makes it different from a plain LLM chat:

- **Retrieval-augmented.** Answers are grounded in real documents stored as embeddings in PostgreSQL via `pgvector`.
- **Live ingestion.** Before the pundit team runs, the pipeline pre-ingests the user's topic from **Wikipedia + sport-specific RSS feeds** so the knowledge base is always populated with fresh evidence. Agents can also pull more on demand mid-conversation, with a 60-minute RSS recency check to avoid redundant scraping.
- **Real-time web fallback.** When the knowledge base still lacks coverage, pundits can call **Tavily** (via MCP) for live web search.
- **Multi-agent debate.** Behind a single "pundit" persona, **specialist AutoGen agents** (Stats, Storyteller, Debater, Predictor, Tactics, Query) collaborate before a Moderator synthesizes one polished answer. A `candidate_func` enforces turn-taking so each specialist speaks at most once.
- **Token streaming.** The Moderator's synthesis is streamed token by token to the client via SSE, with citations sent as a final event.
- **Conversation-scoped memory.** A separate `conversation_memory` vector table remembers facts, opinions and conclusions per chat thread.
- **Sports-only.** A guardrail agent rejects non-sports prompts before any heavy work is done — and can verify uncertain names against Wikipedia before deciding.

> The frontend is built and available at [tactica-frontend](https://github.com/raosam23/tactica-frontend).

---

## How it works

When a user sends a message to `POST /api/conversations/{id}/chat`, this is the flow:

```mermaid
flowchart TD
    A([User message]) --> B{GuardrailAgent<br/>Wikipedia tool}
    B -->|NOT_SPORTS| R([Polite refusal])
    B -->|SPORTS| C[SportDetectorAgent<br/>football / tennis / general]
    C --> D[Persist user message<br/>load last 10 as context]
    D --> E[TopicExtractorAgent<br/>main entity e.g. Lionel Messi]
    E --> F[Pre-ingestion<br/>Wikipedia + sport RSS feeds<br/>RSS skipped if ingested in last 60 min]
    F --> G

    subgraph G [SelectorGroupChat - AutoGen]
        direction TB
        S1[Stats] --- S2[Storyteller] --- S3[Debater]
        S3 --- S4[Predictor] --- S5[Tactics] --- S6[Query]
        S6 --> M[ModeratorPundit<br/>synthesizes, ends with TERMINATE]
    end

    G --> H[Stream tokens over SSE]
    H --> I[Persist assistant message + citations]
    I --> J[MemoryWriter to conversation_memory]
    J --> K[TitleAgent on first turn only]
    K --> Z([Citations event ends stream])
```

**Turn-taking:** a `candidate_func` ensures each specialist speaks at most once and forces `ModeratorPundit` once enough specialists have contributed.

**Termination:** the team stops when `ModeratorPundit` ends its message with `TERMINATE`, or after a message cap as a safety net.

---

## Architecture

```mermaid
flowchart TD
    Client([Client]) --> API[FastAPI - Uvicorn]

    subgraph Routes
        Auth["/api/auth — JWT register / login / me"]
        Conv["/api/conversations — CRUD + /chat - SSE"]
        Msg["/api/conversations/:id/messages"]
    end

    API --> Routes
    Routes --> Services[Services layer<br/>auth · conversation · message · rag · ingestion]
    Services --> Agents[Agents layer<br/>pipeline · agents · tools · group_chat]
    Agents --> DB[(PostgreSQL + pgvector<br/>user · conversation · message<br/>message_citations · document · conversation_memory)]
    Services --> DB
```

---

## Tech stack

| Layer                 | Choice                                       |
| --------------------- | -------------------------------------------- |
| Language              | Python 3.12+                                 |
| API framework         | FastAPI (async)                              |
| Streaming             | Server-Sent Events via `StreamingResponse`   |
| Server                | Uvicorn                                      |
| ORM / models          | SQLModel + SQLAlchemy async                  |
| DB                    | PostgreSQL (Neon-compatible, SSL required)   |
| Vector search         | `pgvector` (cosine distance, dim = 1536)     |
| Migrations            | Alembic (async env)                          |
| Auth                  | JWT (`python-jose`) + `bcrypt` password hash |
| LLM provider          | OpenAI (`gpt-4o-mini` by default)            |
| Embeddings            | OpenAI `text-embedding-3-small`              |
| Multi-agent framework | Microsoft **AutoGen AgentChat**              |
| Web ingestion         | Wikipedia API, RSS via `feedparser`, `httpx` |
| Real-time web search  | **Tavily MCP** (`tavily-mcp` via stdio)      |
| Package manager       | `uv`                                         |

---

## Project layout

```
backend/
├── app/
│   ├── main.py                     # FastAPI app + CORS + /health
│   ├── core/
│   │   └── config.py               # Pydantic settings (.env loader)
│   ├── db/
│   │   └── database.py             # async engine + session factory
│   ├── api/
│   │   ├── router.py               # mounts /api
│   │   └── routes/
│   │       ├── auth.py             # /api/auth/{register,login,me}
│   │       ├── conversations.py    # /api/conversations + /chat (SSE)
│   │       └── messages.py         # /api/conversations/{id}/messages
│   ├── models/                     # SQLModel tables
│   │   ├── user.py
│   │   ├── conversation.py
│   │   ├── message.py
│   │   ├── message_citation.py
│   │   ├── document.py
│   │   └── conversation_memory.py
│   ├── schemas/                    # Pydantic request/response DTOs
│   │   ├── auth.py
│   │   ├── conversation.py
│   │   └── message.py
│   ├── services/                   # business logic
│   │   ├── authentication_service.py
│   │   ├── conversation_service.py
│   │   ├── message_service.py
│   │   ├── rag_service.py          # pgvector cosine search + memory writes
│   │   ├── ingestion_service.py    # scrape -> chunk -> embed -> store
│   │   ├── scraper_service.py      # Wikipedia + RSS
│   │   ├── chunker_service.py      # character chunking with overlap
│   │   └── embedding_service.py    # OpenAI embedding calls
│   ├── agents/                     # AutoGen layer
│   │   ├── model_client.py         # OpenAIChatCompletionClient factory
│   │   ├── agents.py               # AssistantAgent definitions + prompts
│   │   ├── tools.py                # FunctionTool implementations (RAG-backed)
│   │   ├── group_chat.py           # SelectorGroupChat for the pundit team
│   │   └── pipeline.py             # the orchestrator called by /chat
│   └── utils/
│       └── security.py             # JWT, bcrypt, get_current_user dependency
├── alembic/                        # migration env + revisions
├── alembic.ini
├── pyproject.toml                  # deps managed by uv
└── uv.lock
```

---

## Database schema

Six tables, all migrated via Alembic:

| Table                 | Purpose                                                                                              |
| --------------------- | ---------------------------------------------------------------------------------------------------- |
| `user`                | Accounts — email, bcrypt password hash, optional name                                                |
| `conversation`        | Chat threads, scoped to a user                                                                       |
| `message`             | Every user / assistant turn (`role` enum)                                                            |
| `message_citations`   | Many-to-many between assistant messages and the documents that informed them, with `relevance_score` |
| `document`            | **Global RAG store** — text chunks + `VECTOR(1536)` embedding + sport tag + JSONB metadata           |
| `conversation_memory` | **Per-conversation memory** — extracted facts/opinions, embedded for vector lookup                   |

Foreign keys use `ON DELETE CASCADE`, so deleting a conversation cleans up its messages and memory automatically.

---

## Getting started

> Tactica needs **both** repositories. This is the backend — the frontend lives at [tactica-frontend](https://github.com/raosam23/tactica-frontend) and expects this server running on `http://localhost:8000`.

### 1. Prerequisites

- Python **3.12+**
- [`uv`](https://docs.astral.sh/uv/) — `pipx install uv` or follow the official installer
- A PostgreSQL database with the `vector` extension available (Neon works out of the box; the connection requires SSL)
- An OpenAI API key and a Tavily API key

### 2. Clone the repository

```bash
git clone https://github.com/raosam23/tactica-backend
cd tactica-backend
```

### 3. Install dependencies

```bash
uv sync
```

### 4. Configure environment

Create a `.env` in the project root — see [Environment variables](#environment-variables).

### 5. Run migrations

```bash
uv run alembic upgrade head
```

This creates all six tables and enables the `pgvector` extension.

### 6. Start the server

```bash
uv run uvicorn app.main:app --reload
```

| Surface      | URL                            |
| ------------ | ------------------------------ |
| Health check | `http://127.0.0.1:8000/health` |
| Swagger UI   | `http://127.0.0.1:8000/docs`   |
| ReDoc        | `http://127.0.0.1:8000/redoc`  |

---

## Environment variables

Loaded from `.env` via `pydantic-settings`.

| Variable                      | Required | Default                                              | Notes                                     |
| ----------------------------- | :------: | ---------------------------------------------------- | ----------------------------------------- |
| `APP_NAME`                    |    No    | `Tactica`                                            |                                           |
| `APP_ENV`                     |    No    | `development`                                        |                                           |
| `DEBUG`                       |    No    | `True`                                               | Enables SQLAlchemy `echo`                 |
| `DATABASE_URL`                |   Yes    | —                                                    | Must be `postgresql+asyncpg://...`        |
| `SECRET_KEY`                  |   Yes    | —                                                    | JWT signing secret                        |
| `ALGORITHM`                   |    No    | `HS256`                                              |                                           |
| `ACCESS_TOKEN_EXPIRE_MINUTES` |    No    | `30`                                                 |                                           |
| `SALT_ROUNDS`                 |    No    | `12`                                                 | bcrypt cost                               |
| `OPENAI_API_KEY`              |   Yes    | —                                                    |                                           |
| `OPENAI_MODEL`                |    No    | `gpt-4o-mini`                                        | Used by every agent                       |
| `EMBEDDING_MODEL`             |    No    | `text-embedding-3-small`                             |                                           |
| `VECTOR_DIMENSION`            |    No    | `1536`                                               | Must match the embedding model            |
| `TAVILY_API_KEY`              |   Yes    | —                                                    | Used by pundits via the Tavily MCP server |
| `ALLOWED_ORIGINS`             |    No    | `["http://localhost:3000", "http://localhost:8000"]` | CORS allowlist                            |

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

TAVILY_API_KEY=tvly-...
```

> The async engine is created with `connect_args={"ssl": "require"}`. Use a Postgres host that accepts SSL (Neon, Supabase, RDS, etc.).

---

## API reference

All routes are mounted under the `/api` prefix. Every protected route expects:

```http
Authorization: Bearer <jwt>
```

### Route map

| Method | Path                                            | Auth | Purpose                                   |
| :----: | ----------------------------------------------- | :--: | ----------------------------------------- |
|  GET   | `/health`                                       |  No  | Liveness probe                            |
|  POST  | `/api/auth/register`                            |  No  | Create user, return user object           |
|  POST  | `/api/auth/login`                               |  No  | Verify credentials, return JWT            |
|  GET   | `/api/auth/me`                                  | Yes  | Get current user's profile                |
| DELETE | `/api/auth/me`                                  | Yes  | Delete the current user's account         |
|  POST  | `/api/conversations/`                           | Yes  | Create a new conversation                 |
|  GET   | `/api/conversations/`                           | Yes  | List the current user's conversations     |
|  GET   | `/api/conversations/{conversation_id}`          | Yes  | Fetch a single conversation               |
| DELETE | `/api/conversations/{conversation_id}`          | Yes  | Delete a conversation (cascades messages) |
|  POST  | `/api/conversations/{conversation_id}/chat`     | Yes  | **Run the pipeline, stream over SSE**     |
|  GET   | `/api/conversations/{conversation_id}/messages` | Yes  | List all messages in a conversation       |

<details>
<summary><strong>POST /api/auth/register</strong> — 201 Created</summary>

Request:

```json
{ "email": "user@example.com", "password": "strongpass", "name": "Samarth" }
```

- `email` must be a valid email address (validated via `EmailStr`)
- `password` must be at least 8 characters

Response:

```json
{ "id": "uuid", "email": "user@example.com", "name": "Samarth" }
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

Request (title is optional — if omitted, the `TitleAgent` generates one after the first chat turn):

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
<summary><strong>POST /api/conversations/{conversation_id}/chat</strong> — 200 OK (SSE stream)</summary>

Request:

```json
{ "message": "Was Barcelona's 2011 team better than Manchester City's treble side?" }
```

Response: `text/event-stream` — a stream of SSE events. Each event carries a JSON payload:

**Token event** (one per token, streamed in real time):

```
data: {"type": "token", "content": "Barcelona"}
```

**Citations event** (sent once at the end, signals the stream is complete):

```
data: {"type": "citations", "citations": [{"source": "FC Barcelona - wikipedia", "relevance_score": 0.48}]}
```

Citations are deduplicated by source — only the highest relevance score is kept per unique source.

What this endpoint does under the hood:

1. Verifies the conversation belongs to the caller.
2. Runs the **GuardrailAgent** (Wikipedia-tooled). If the prompt is not sports-related, streams a polite refusal and stops.
3. Runs the **SportDetectorAgent** to tag the query (e.g. `football`, `tennis`, or `general`).
4. Loads the last 10 messages as context, persists the user message.
5. Runs the **TopicExtractorAgent** to extract the main sports entity (player, team, tournament).
6. **Pre-ingests** the topic from Wikipedia + sport-specific RSS feeds before any pundit runs (RSS skipped if a non-Wikipedia document was ingested in the last 60 minutes).
7. Runs a **`SelectorGroupChat`** with a `candidate_func` that prevents repeats and forces `ModeratorPundit` after enough specialists have spoken. The Moderator's tokens are streamed to the client as they are generated.
8. Persists the assistant's final reply, plus citations into `message_citations`, then sends the citations event.
9. Runs the **MemoryWriter** agent over the exchange to extract durable facts into `conversation_memory`.
10. If the conversation has no title yet, runs the **TitleAgent**.

</details>

<details>
<summary><strong>GET /api/conversations/{conversation_id}/messages</strong> — 200 OK</summary>

Response (each assistant message also includes a deduplicated `citations` array):

```json
[
    {
        "id": "uuid",
        "conversation_id": "uuid",
        "role": "user",
        "content": "...",
        "citations": [],
        "created_at": "2026-05-05T10:01:00Z"
    },
    {
        "id": "uuid",
        "conversation_id": "uuid",
        "role": "assistant",
        "content": "...",
        "citations": [{ "source": "FC Barcelona - wikipedia", "relevance_score": 0.48 }],
        "created_at": "2026-05-05T10:01:05Z"
    }
]
```

</details>

### Quick `curl` walkthrough

```bash
# 1. Register
curl -s -X POST http://127.0.0.1:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"u@x.com","password":"hunter22","name":"Michael Scott"}'

# 2. Login and capture the token
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"u@x.com","password":"hunter22"}' \
  | jq -r '.access_token')

# 3. Create a conversation
CID=$(curl -s -X POST http://127.0.0.1:8000/api/conversations/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}' | jq -r '.id')

# 4. Talk to the pundit (streams SSE)
curl -N -X POST "http://127.0.0.1:8000/api/conversations/$CID/chat" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"Who had the greater peak — Messi or Maradona?"}'

# 5. Read the thread
curl "http://127.0.0.1:8000/api/conversations/$CID/messages" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Agent pipeline

All agents are `autogen_agentchat.agents.AssistantAgent` instances backed by the same `OpenAIChatCompletionClient`, split into two layers.

### Pre-pipeline agents

| Agent                   | Tools              | Job                                                                                               |
| ----------------------- | ------------------ | ------------------------------------------------------------------------------------------------- |
| **GuardrailAgent**      | `search_wikipedia` | Replies with exactly `SPORTS` or `NOT_SPORTS`. Looks up unfamiliar names on Wikipedia when unsure |
| **SportDetectorAgent**  | none               | Returns the lowercase sport name, or `general` if it can't decide                                 |
| **TopicExtractorAgent** | none               | Extracts the main sports entity from the message (player, team, tournament) for pre-ingestion     |

### Pundit team (`SelectorGroupChat`)

| Agent                 | Job                                                                            |
| --------------------- | ------------------------------------------------------------------------------ |
| **StatsPundit**       | Pulls precise statistics, comparisons and records                              |
| **StorytellerPundit** | Adds narrative, history, career arcs and historical parallels                  |
| **DebaterPundit**     | Fact-checks claims and surfaces opposing viewpoints                            |
| **PredictorPundit**   | Makes bold, evidence-based predictions about outcomes, careers, and trends     |
| **TacticsPundit**     | Breaks down tactical formations, game plans, and coaching decisions            |
| **QueryPundit**       | Answers simpler direct questions using Tavily web search                       |
| **ModeratorPundit**   | Synthesizes everything into a single opinionated answer; ends with `TERMINATE` |

The team is governed by a **`candidate_func`** that prevents agents from being selected twice and forces `ModeratorPundit` once enough specialists have spoken. A **`selector_prompt`** further guides the LLM to pick the most relevant unspoken specialist for each turn. The Moderator runs with `model_client_stream=True` so its tokens can be streamed to the client.

### Side-effect agents

| Agent            | Job                                                                                  |
| ---------------- | ------------------------------------------------------------------------------------ |
| **MemoryWriter** | Reads the user/assistant exchange and writes useful facts into `conversation_memory` |
| **TitleAgent**   | Generates a short title for the conversation if it doesn't have one yet              |

---

## Agent tools

All tools are `FunctionTool` wrappers around async Python functions in `app/agents/tools.py`. Each one is a thin wrapper over the RAG / ingestion services.

| Tool                      | Used by                         | What it does                                                                    |
| ------------------------- | ------------------------------- | ------------------------------------------------------------------------------- |
| `search_stats`            | Stats, Predictor, Tactics       | Cosine similarity over `document`, returns top-k snippets + sources             |
| `compare_players`         | Stats, Predictor, Tactics       | Runs `search_stats` for each player and groups results                          |
| `search_articles`         | Storyteller, Tactics            | Same vector search, framed for narrative content                                |
| `get_historical_parallel` | Storyteller, Predictor, Tactics | Vector search aimed at finding analogous past events                            |
| `fact_check`              | Debater                         | Vector search for evidence supporting/contradicting a claim                     |
| `search_opposing_view`    | Debater                         | Vector search aimed at counter-perspectives                                     |
| `search_memory`           | All pundits                     | Cosine similarity over `conversation_memory` (scoped to this conversation)      |
| `ingest_and_search`       | All pundits                     | Live Wikipedia + (recency-checked) RSS ingestion, then `search_stats`           |
| `tavily_search` (MCP)     | All pundits                     | Real-time web search fallback when the knowledge base lacks sufficient coverage |
| `search_wikipedia`        | GuardrailAgent                  | Standalone Wikipedia lookup used purely for sport-topic verification            |
| `add_memory`              | MemoryWriter                    | Embeds and writes a fact into `conversation_memory`                             |

Whenever a search tool returns a hit, the document's `(id, score)` is recorded in a per-request `cited_documents` list. After the moderator finishes, those citations are persisted into `message_citations`.

---

## Roadmap

The backend is functional end-to-end. Known follow-ups:

- **Richer ingestion.** More sources beyond Wikipedia + RSS; an internal admin endpoint to trigger ingestion explicitly.
- **Observability.** Per-turn traces for retrieval quality, tool calls, and agent decisions.

---

<div align="center">
  <sub>Built for sports conversations that feel <b>opinionated, informed, and context-aware</b>.</sub>
</div>
