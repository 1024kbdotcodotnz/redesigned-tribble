# AEGIS — Admin Collections, GPU Release & Login Concurrency Design

**Date:** 2026-06-25  
**Scope:** API (`api/server.py`, `core/agent_swarm.py`, `core/rag_engine.py`) and Streamlit frontend (`web/streamlit_app.py`)

## 1. Problem Statement

The user reports several operational issues and missing admin features:

1. **GPU stays at full load after analysis finishes** — the Ollama model is kept in VRAM long after `/api/v1/analyse/disclosure` returns.
2. **A second visitor cannot log in while one analysis is running** — long-running analysis appears to block or starve the single Uvicorn worker / default thread pool, preventing concurrent login.
3. **Collection Manager is empty** — the admin/staff "Collection Manager" page only lists collection names; admins cannot add or remove collections from the UI.
4. **No way to inspect collection contents** — admins cannot "dive into" a collection to verify what documents/chunks are actually stored.
5. **Upload is missing from the radio menu** — the "Upload" page is in the sidebar list but has syntax errors and no `main()` branch, so it is unreachable. The user wants it restored **only for permanent uploads** to collections.

## 2. Goals

- Release GPU memory promptly after a disclosure analysis completes.
- Keep login/auth endpoints responsive even while a long analysis is running.
- Let admin/staff create and delete collections from the Collection Manager UI.
- Let admin/staff browse collection documents/chunks and metadata (collection inspector).
- Restore the "Upload" radio-button page, scoped to permanent collection uploads only.
- Make minimal changes to existing flows and preserve backward compatibility.

## 3. Proposed Approaches

### 3.1 GPU Release

**Option A — Short Ollama keep-alive everywhere**
Change `keep_alive` from `"30m"` to `"0"` in `OllamaLLMClient.generate` so Ollama unloads the model after every call. Simple but increases latency for sequential calls.

**Option B — Explicit unload after analysis (recommended)**
Keep the model loaded during analysis for speed, then send an Ollama `/api/generate` request with `"keep_alive": 0` and an empty prompt after `swarm.analyse_disclosure()` returns. This releases VRAM without penalising every individual LLM call. Add a small helper `ollama_unload_model()` and call it in a `finally` block in the analysis endpoint.

### 3.2 Login Concurrency

**Option A — Increase Uvicorn workers**
Set default `UVICORN_WORKERS` higher. On fractional-GPU / single-CPU RunPod pods this may not help and can increase memory use.

**Option B — Convert auth paths to async + cache demo state (recommended)**
Make `/api/v1/login`, demo auth, and tenant lookups non-blocking. Add a short-lived in-memory cache for demo sessions so `get_current_demo_or_tenant` does not repeatedly hit disk. Add an `asyncio.Semaphore` around the analysis call so only one analysis runs at a time but the event loop remains free for login/auth traffic.

### 3.3 Collection Manager / Inspector / Upload

Only one reasonable approach: add API endpoints for collection CRUD and inspection, then wire them into the Streamlit UI.

## 4. Design

### 4.1 Backend Changes

#### 4.1.1 GPU Release Helper

Add to `core/agent_swarm.py` or a new `core/ollama_utils.py`:

```python
def ollama_unload_model(model: str, host: str = "http://localhost:11434") -> None:
    requests.post(
        f"{host}/api/generate",
        json={"model": model, "prompt": "", "stream": False, "keep_alive": 0},
        timeout=30,
    )
```

Call this in `api/server.py` inside a `finally` block after `swarm.analyse_disclosure()` returns.

#### 4.1.2 Concurrency Guard

In `api/server.py`, wrap the analysis call with an `asyncio.Semaphore(value=1)` module-level guard:

```python
_analysis_semaphore = asyncio.Semaphore(1)

async def analyse_disclosure(...):
    async with _analysis_semaphore:
        ...  # existing logic
```

This ensures only one analysis runs at a time, but the event loop can still accept and process login requests. Convert `/api/v1/login` and demo auth helpers to async where possible; keep file I/O behind `asyncio.to_thread`.

#### 4.1.3 Collection CRUD Endpoints

Add admin/staff endpoints under `/api/v1/admin/collections`:

- `GET /api/v1/admin/collections` — list all collections with document counts (already exists as `/api/v1/collections`; extend to include all Chroma collections, not just `engine.COLLECTIONS`).
- `POST /api/v1/admin/collections/{name}` — create a new empty collection. Requires admin or staff role.
- `DELETE /api/v1/admin/collections/{name}` — delete a collection. Requires admin role only (staff cannot delete permanent data).
- `GET /api/v1/admin/collections/{name}/inspect` — return paginated chunks with metadata (ids, documents, metadatas). Supports `limit`/`offset` query params.

#### 4.1.4 Collection Listing Fix

Update `/api/v1/admin/stats` and `/api/v1/collections` to list **all** Chroma collections (not only the hard-coded `engine.COLLECTIONS`), so user-created collections appear.

### 4.2 Frontend Changes

#### 4.2.1 Fix Sidebar Syntax

In `show_sidebar()`, fix the missing commas in the `pages` lists and add an `"Upload"` branch in `main()`.

#### 4.2.2 Restore Upload Page (Permanent Only)

`show_upload()` should remain available but simplified for permanent uploads:
- Keep collection selection (create new or add to existing).
- Remove the "Temporary session" option for privileged users from the radio menu, or keep it disabled with a note that temporary upload is now part of Defence Analysis.
- Keep the existing upload button and server call to `/api/v1/upload/files` / `/api/v1/upload/zip`.
- Do not auto-redirect to Defence Analysis; stay on Upload and show success.

#### 4.2.3 Collection Manager Page

Expand `show_collection_manager()` to:
- Show a table of collections with document counts.
- Provide a "Create collection" form (name + optional description).
- Provide a "Delete collection" button with confirmation (admin only).
- Let the user select a collection and click "Inspect" to open the inspector.

#### 4.2.4 Collection Inspector Page

Add `show_collection_inspector()`:
- Select a collection.
- Show paginated chunks (id, source/filename, page, snippet).
- Display aggregate metadata: total chunks, unique source documents.
- Useful for verifying that uploaded documents were chunked correctly.

### 4.3 Data Model / State

No new persistent state beyond existing ChromaDB. Collection metadata uses Chroma collection `metadata` field. Demo-session state remains in JSON files but gets short in-memory caching to reduce disk contention.

## 5. Error Handling

- GPU unload failures are logged but never fail the API response.
- Collection deletion requires admin role and shows a confirmation dialog in Streamlit.
- Attempting to delete system collections (`nz_legislation`, `nz_case_law`, `nz_police_manual`) is rejected.
- Collection creation with invalid names is rejected (alphanumeric, dash, underscore only).
- Inspector pagination defaults to 20 chunks per page.

## 6. Testing

- Run `python -m py_compile api/server.py web/streamlit_app.py core/agent_swarm.py`.
- Start the API and verify login works while a long analysis is running.
- Verify GPU VRAM drops after analysis via `nvidia-smi` or Ollama logs.
- Create/delete/inspect collections through the UI.
- Verify the Upload page is reachable from the radio menu and only performs permanent uploads.

## 7. Files to Modify

- `api/server.py` — GPU unload, semaphore, collection CRUD/inspect endpoints, async auth improvements.
- `web/streamlit_app.py` — sidebar fix, Upload page restore, Collection Manager, Collection Inspector.
- `core/agent_swarm.py` — add Ollama unload helper.
- `core/rag_engine.py` — optional helper to list all collections and get collection chunks.
