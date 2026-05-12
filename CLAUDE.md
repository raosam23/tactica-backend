# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Run the server:**
```bash
uv run uvicorn app.main:app --reload
```

**Database migrations:**
```bash
# Create a new migration (autogenerate from model changes)
uv run alembic revision --autogenerate -m "description"

# Apply migrations
uv run alembic upgrade head

# Downgrade one step
uv run alembic downgrade -1
```

**Linting / type checking:**
```bash
uv run ruff check .
uv run pyright
```

**Package management:** uses `uv`. Add dependencies with `uv add <package>`, not pip.

## Project structure

```
app/
├── main.py                  # FastAPI app, CORS middleware, router mount
├── core/
│   └── config.py            # Settings (pydantic-settings), SPORT_RSS_FEEDS map
├── api/
│   ├── router.py            # Top-level /api router
│   └── routes/
│       ├── auth.py          # /auth/* endpoints
│       ├── conversations.py # /conversations/* endpoints + /chat
│       └── messages.py      # /conversations/{id}/messages
├── agents/
│   ├── agents.py            # All AutoGen agent definitions (pundit panel + pipeline agents)
│   ├── group_chat.py        # SelectorGroupChat team setup + candidate_selector_function
│   ├── pipeline.py          # run_chat_pipeline — main orchestration entry point
│   ├── tools.py             # make_tools() closure factory for RAG tools; search_wikipedia
│   └── model_client.py      # OpenAIChatCompletionClient factory
├── services/
│   ├── ingestion_service.py # run_ingestion (scrape → chunk → embed → store)
│   ├── rag_service.py       # Vector search services (documents + conversation memory)
│   ├── scraper_service.py   # Wikipedia + RSS feed scrapers
│   ├── chunker_service.py   # Text chunking with overlap
│   ├── embedding_service.py # OpenAI embedding calls
│   ├── authentication_service.py
│   ├── conversation_service.py
│   └── message_service.py
├── models/                  # SQLModel ORM models (map 1:1 to DB tables)
│   ├── user.py
│   ├── conversation.py
│   ├── message.py
│   ├── message_citation.py
│   ├── document.py          # Stores chunked text + pgvector embedding
│   └── conversation_memory.py
├── schemas/                 # Pydantic request/response schemas
│   ├── auth.py
│   ├── conversation.py
│   └── message.py
├── db/
│   └── database.py          # Async engine, session maker, get_session dependency
└── utils/
    └── security.py          # JWT helpers, get_current_user dependency

alembic/                     # Database migrations
├── env.py                   # Imports all models for autogenerate support
└── versions/                # Migration scripts
```

## Architecture

Tactica is a sports AI chatbot backend built with FastAPI + async SQLAlchemy (SQLModel), backed by PostgreSQL with pgvector for semantic search.

### Request flow

A `POST /api/conversations/{id}/chat` request triggers `run_chat_pipeline` in `app/agents/pipeline.py`, which is the central orchestration function:

1. **Guardrail** — `GuardrailAgent` rejects non-sports queries.
2. **Sport detection** — `SportDetectorAgent` classifies the sport category.
3. **Ingestion** — `run_ingestion` scrapes Wikipedia (for the topic entity) and sport-specific RSS feeds, chunks the text, embeds it with OpenAI `text-embedding-3-small`, and upserts into the `document` table. RSS scraping is skipped if docs were ingested within the last hour.
4. **Panel discussion** — An AutoGen `SelectorGroupChat` team (see `app/agents/group_chat.py`) selects 4+ specialist agents from the panel and then calls `ModeratorPundit` to synthesize a final response ending with `TERMINATE`.
5. **Post-processing** — `MemoryWriter` agent stores key facts as vector embeddings in `conversation_memory`. `TitleAgent` sets the conversation title on the first message.

### Agent panel (`app/agents/agents.py`)

Seven specialist agents with distinct roles and tool sets:
- **StatsPundit** — numerical stats, player comparisons
- **StorytellerPundit** — narrative context, career arcs
- **DebaterPundit** — fact-checking, opposing views
- **PredictorPundit** — forecasting, historical precedents
- **TacticsPundit** — formations, game plans, coaching
- **QueryPundit** — general sports Q&A (Tavily only, for simple questions)
- **ModeratorPundit** — always speaks last; synthesizes all inputs into one response

All specialist agents share access to Tavily MCP tools (web search) via `StdioServerParams` calling `npx -y tavily-mcp`. RAG tools (`search_stats`, `search_articles`, `ingest_and_search`, etc.) are closures created in `app/agents/tools.py` via `make_tools`, capturing the DB session and a shared `cited_documents` list for citation tracking.

### RAG layer (`app/services/`)

- **`rag_service.py`** — `SearchDocumentsService` (cosine distance on `pgvector`), `SearchConversationMemoryService`, `AddConversationMemoryService`
- **`ingestion_service.py`** — `run_ingestion` orchestrates scrape → chunk → embed → store
- **`scraper_service.py`** — Wikipedia and RSS feed scrapers
- **`chunker_service.py`** — text chunking with overlap
- **`embedding_service.py`** — OpenAI embedding calls

### Data models (`app/models/`)

All models use `SQLModel` (SQLAlchemy + Pydantic hybrid). Key models:
- `User` — JWT-authenticated users
- `Conversation` — belongs to a user; title set after first message
- `Message` — role (`user`/`assistant`), belongs to conversation
- `MessageCitation` — links messages to `Document` rows with a relevance score
- `Document` — chunked text with `Vector(1536)` embedding, sport tag, JSONB metadata
- `ConversationMemory` — per-conversation key facts with `Vector(1536)` embedding

### API routes (`app/api/routes/`)

All routes are prefixed `/api`:
- `POST /auth/register`, `POST /auth/login`, `GET /auth/me`, `DELETE /auth/me`
- `GET/POST /conversations/`, `GET/DELETE /conversations/{id}`
- `POST /conversations/{id}/chat` — main entry point
- `GET /conversations/{id}/messages`

Auth uses JWT Bearer tokens via `python-jose`; `get_current_user` dependency in `app/utils/security.py`.

## Environment variables

Required in `.env`:
```
DATABASE_URL=postgresql+asyncpg://...   # must use asyncpg driver
SECRET_KEY=...
OPENAI_API_KEY=...
TAVILY_API_KEY=...
```

Optional (with defaults): `OPENAI_MODEL` (gpt-4o-mini), `EMBEDDING_MODEL` (text-embedding-3-small), `VECTOR_DIMENSION` (1536), `ACCESS_TOKEN_EXPIRE_MINUTES` (30).

## Key conventions

- Service functions are named `<Verb><Entity>Service` (e.g., `CreateConversationService`) and live in `app/services/`.
- DB column name collisions with reserved names use a trailing underscore on the attribute (e.g., `metadata_` maps to the `metadata` column).
- The `cited_documents` list in `make_tools` is a mutable list captured by closure — all RAG tool calls append `(doc_id, score)` to it for later citation tracking.
- Alembic imports all models explicitly in `alembic/env.py` to ensure autogenerate detects schema changes.
