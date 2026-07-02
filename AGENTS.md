# AEGIS / NZ Legal RAG — Agent Guide

## Project Overview

**AEGIS** (also called *NZ Legal RAG* / *NZ Criminal Disclosure RAG*) is a New Zealand criminal-defence research and disclosure-analysis system. It runs entirely on local hardware using Ollama for LLM inference and embeddings, ChromaDB for vector storage, FastAPI for the backend, and Streamlit for the web UI.

The system ingests NZ legal sources (legislation, NZLII case law, Police Manual chapters) plus user-uploaded criminal-disclosure bundles, then produces structured legal-analysis reports from the perspective of senior defence counsel. All outputs carry a disclaimer that they are co-counsel assistance only, not definitive legal advice.

> **Project root:** `C:/Users/megab/aegis`  
> **Canonical code:** repo root. Treat `nz_legal_rag_deploy/` as an older deployment snapshot, not the source of truth.

## Technology Stack

| Layer | Technology | Notes |
|---|---|---|
| Language | Python 3.11+ | Docker images use `python:3.11-slim`; `setup.py` rejects Python < 3.10 |
| LLM / embeddings | Ollama, `langchain-ollama` | Default embedding model `nomic-embed-text`; default LLM varies by entry point |
| Vector DB | ChromaDB `0.5.4` | Persistent storage in `chroma_db/` or `/workspace/chroma_db_fresh` |
| API | FastAPI + Uvicorn, Pydantic v2 | Version declared in `api/server.py`: `1.2.2` |
| Web UI | Streamlit `>=1.42.0` | `web/streamlit_app.py` |
| MCP | `fastmcp>=2.0.0` | `api/mcp_server.py` |
| Document parsing | `PyPDF2`, `python-docx`, `openpyxl`, `beautifulsoup4`, `lxml` | Plus `core/file_parser.py` |
| Report export | `python-docx`, `fpdf2>=2.7.0`, `docx2pdf>=0.1.8` | `core/report_export.py` |
| Security | `cryptography>=41.0.0` | Fernet encryption, PBKDF2 key derivation |
| Testing | `pytest>=8.0.0`, `pytest-asyncio>=0.23.0` | Tests live in `tests/` |
| Deployment | Docker Compose + shell scripts | RunPod and Vultr GPU deployment scripts at repo root |

There is **no `pyproject.toml`, `setup.cfg`, `pytest.ini`, or `tox.ini`**. Dependencies are declared only in `requirements.txt`.

## Architecture

### Runtime Components

```text
┌─────────────────┐     HTTP      ┌──────────────────────────┐
│  Streamlit Web  │◄─────────────►│  FastAPI server (api/)   │
│ web/streamlit_  │               │  api/server.py           │
│ app.py          │               │  Port 8000 (default)     │
└─────────────────┘               └────────────┬─────────────┘
                                               │
                         ┌─────────────────────┼─────────────────────┐
                         │                     │                     │
                         ▼                     ▼                     ▼
                   ┌──────────┐        ┌─────────────┐        ┌────────────┐
                   │  MCP     │        │ Email bridge│        │ Admin/     │
                   │  server  │        │ services/   │        │ Demo auth  │
                   │api/mcp_  │        │ api/email_  │        │ security/  │
                   │server.py │        │ routes.py   │        │ tenant_    │
                   └──────────┘        └─────────────┘        │ manager.py │
                                                              └────────────┘
                                               │
                                               ▼
                              ┌────────────────────────────────┐
                              │  core/rag_engine.py            │
                              │  NZLegalRAG                    │
                              │  ChromaDB + OllamaEmbeddings   │
                              └────────────────────────────────┘
                                               │
                              ┌────────────────┴────────────────┐
                              ▼                                 ▼
                   ┌─────────────────────┐          ┌──────────────────────┐
                   │  Multi-agent swarm  │          │  Document parsers    │
                   │  core/agent_swarm.py│          │  core/parser.py      │
                   │  core/rag_integration│          │  core/file_parser.py │
                   └─────────────────────┘          └──────────────────────┘
```

- **`api/server.py`** — Main FastAPI module (~2,000 lines). Holds the `NZLegalRAG` singleton, demo/session JSON-file storage, tenant auth, upload/ingest/analysis endpoints, and temporary upload collection management.
- **`web/streamlit_app.py`** — Streamlit frontend (~1,800 lines). Talks to `api/server.py` over HTTP via `API_URL`.
- **`api/mcp_server.py`** — FastMCP server exposing legal-search tools. Supports `stdio`, `sse`, and `streamable-http` transports.
- **`services/email_*.py` + `api/email_routes.py`** — Optional IMAP/SMTP email disclosure bridge. Disabled by default.

### Analysis Pipeline (`core/agent_swarm.py`)

1. **Parser** — `DisclosureParser` extracts charges, facts, warrants, etc.
2. **FactSheetBuilder** — Builds an anchored fact sheet from parsed disclosure.
3. **IssueSpotter** — Ranks defence issues and selects a central theory.
4. **QueryGen** — Generates RAG queries.
5. **RAG Retrieval** — Searches ChromaDB collections.
6. **Six parallel KCs** — Strategist, Evidential, Rights, Admissions, Cross-Examination, Disclosure/Forensic (throttled to 2 concurrent calls).
7. **Orchestrator / Synthesis** — Combines KC outputs into `SynthesizedReport`.
8. **Citation Auditor + Verification pass** — Verifies final report against sources and flags unanchored claims.

### Key Data Directories

| Path | Purpose | Gitignored |
|---|---|---|
| `chroma_db/` or `/workspace/chroma_db_fresh` | Vector database | yes |
| `tenant_data/` | Tenant/API-key files | yes |
| `secure_data/` | Encrypted confidential docs | yes |
| `demo_sessions/`, `temp_sessions/` | Session state and temp uploads | yes |
| `data/legislation/`, `data/case_law/`, `data/police_manual/` | NZ legal source data | no (contents may be generated) |
| `logs/` | Application logs | yes |

## Main Entry Points & Commands

### Local Development

```bash
# 1. Create venv and install dependencies
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Run interactive setup (pulls Ollama models, creates .env, dirs, samples)
python setup.py

# 3. Start Ollama locally, then run the backend
python -m api.server             # http://localhost:8000  (Swagger at /docs)

# 4. In another terminal, run the web UI
streamlit run web/streamlit_app.py   # http://localhost:8501
```

Or use the wrapper:

```bash
./start.sh                       # Uses .venv/bin/python, starts API + web, optional MCP
```

### Docker Compose

```bash
# Local full-GPU deployment (API mapped to host port 8080; web on 8501; Ollama on 11434)
docker compose up -d --build

# Vultr GPU deployment
docker compose -f docker-compose.vultr.yml up -d --build

# Fractional-GPU deployment
COMPOSE_FILE=docker-compose.fractional.yml docker compose up -d --build
```

> **Port conflict note:** In `docker-compose.yml`, both the `api` service and the `mcp` service map to host port `8080`. Review port mappings before deploying.

### Data Ingestion

```bash
python -m ingestion.nzleg_scraper
python -m ingestion.police_manual_scraper
```

These create JSON source files in `data/`. Vector collections (`nz_legislation`, `nz_case_law`, `nz_police_manual`) are populated by the scrapers or by API ingestion endpoints.

### MCP Server

```bash
# stdio (for local MCP clients)
python -m api.mcp_server --transport stdio

# HTTP/SSE
python -m api.mcp_server --transport streamable-http --host 0.0.0.0 --port 8080 --path /mcp
```

`mcp_stdio_proxy.py` is configured in `claude_desktop_config.json` and `.cursor/mcp.json` to proxy stdio to `http://localhost:8080/mcp`.

### Testing

```bash
pytest tests/                    # maintained suite (no legacy root-level scripts)
pytest tests/test_parser.py tests/test_report_export.py tests/services/ tests/api/test_email_routes.py
```

Avoid bare `pytest` from the repo root — it also collects `test_pipeline.py`, which is a legacy diagnostic script not maintained for pytest.

## Key File Map

| File | Role |
|---|---|
| `api/server.py` | Main FastAPI REST backend |
| `api/mcp_server.py` | MCP server |
| `api/auth.py` | Session-token auth helpers |
| `api/email_routes.py` | Admin endpoints for email bridge |
| `web/streamlit_app.py` | Main Streamlit UI |
| `core/rag_engine.py` | `NZLegalRAG` retrieval/generation engine |
| `core/agent_swarm.py` | Multi-agent KC pipeline orchestration |
| `core/rag_integration.py` | Wires swarm into `NZLegalRAG` |
| `core/parser.py` | `DisclosureParser` |
| `core/fact_sheet.py` | Fact-sheet dataclasses |
| `core/fact_sheet_builder.py` | Builds fact sheets from parsed disclosure |
| `core/issue_spotter.py` | Selects central defence theory |
| `core/verification.py` | Flags unanchored claims in reports |
| `core/report_export.py` | DOCX/PDF/HTML report builders |
| `core/file_parser.py` | Upload file parsing |
| `security/tenant_manager.py` | API-key / tenant management |
| `security/confidential_processor.py` | PII redaction + encryption |
| `services/email_*.py` | Email bridge |
| `ingestion/*.py` | Legislation and Police Manual scrapers |
| `requirements.txt` | All Python dependencies |
| `setup.py` | Interactive setup script |

## Environment & Configuration

`.env` is loaded from the project root by `api/server.py` and `web/streamlit_app.py`:

```python
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
```

Key variables:

```bash
CHROMA_DB_PATH=./chroma_db
TENANT_DATA_PATH=./tenant_data
OLLAMA_HOST=http://localhost:11434
EMBEDDING_MODEL=nomic-embed-text
LLM_MODEL=mixtral:latest          # setup.py default
API_HOST=0.0.0.0
API_PORT=8000
ADMIN_API_KEY=change-this-in-production
AEGIS_EMAIL_POLLER_ENABLED=false
```

## Code Conventions

- **Python 3.11-compatible** code.
- Use type hints where they already appear (`dict[str, Any]`, `Optional`, `List`, dataclasses, Pydantic `BaseModel`).
- Prefer **f-strings** for new code.
- Many modules **lazily import** optional dependencies inside functions; follow that pattern.
- **Print-based operational logging** is common (e.g., `[AGENT_SWARM] ...`); do not replace with a logging framework unless asked.
- Be **defensive**: broad `try/except` fallbacks are intentional because the system must keep running if a model call or collection lookup fails.
- When extending report dataclasses, provide **default values** to preserve backward compatibility.
- **Naming:** `snake_case` functions/variables, `PascalCase` classes, `UPPER_CASE` module constants.
- Recent commits use **Conventional Commits** (`feat:`, `fix:`, `docs:`, `test:`).

## Testing Conventions

- Framework: `pytest` + `pytest-asyncio`.
- `tests/conftest.py` only adds the project root to `sys.path`.
- Tests are organized by module.
- External-file tests skip gracefully:
  ```python
  if not file_path.exists():
      pytest.skip(f"File not found: {file_path}")
  ```
- Dependency injection is preferred for testability (e.g., `IssueSpotter` accepts an LLM client).

## Common Pitfalls

- Do not introduce a `pyproject.toml` or formatter config without team agreement.
- Do not remove print-based operational logging unless asked.
- When adding fields to shared dataclasses, always provide defaults.
- Be careful with Windows-absolute paths in tests; gate or parameterize them.
- `docker-compose.yml` has an API/MCP host port conflict on `8080`.
- Ollama model defaults vary by entry point; always verify `LLM_MODEL` in production.
- ChromaDB path defaults differ locally (`./chroma_db`) vs. cloud (`/workspace/chroma_db_fresh`).
