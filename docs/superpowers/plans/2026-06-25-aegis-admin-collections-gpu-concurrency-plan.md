# AEGIS Admin Collections, GPU Release & Login Concurrency — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add collection management/inspection to the admin UI, release GPU memory after analysis, keep login responsive during analysis, and restore the permanent-only Upload page.

**Architecture:** Add an explicit Ollama unload helper called after analysis; guard analysis with an `asyncio.Semaphore`; add admin collection CRUD/inspect API endpoints; extend the Streamlit Collection Manager and add a Collection Inspector; fix the sidebar and restore Upload for permanent collections only.

**Tech Stack:** Python 3.11+, FastAPI, Streamlit, ChromaDB, Ollama, asyncio.

---

## File Map

| File | Responsibility |
|---|---|
| `core/agent_swarm.py` | Add `ollama_unload_model()` helper; source of truth for the model `host` used by `OllamaLLMClient`. |
| `core/rag_engine.py` | Add `list_all_collections()` and `inspect_collection()` helpers that talk to ChromaDB directly. |
| `api/server.py` | GPU unload in analysis endpoint; analysis semaphore; async auth improvements; new collection CRUD/inspect endpoints; update stats/collections listing. |
| `web/streamlit_app.py` | Fix sidebar page lists; restore Upload page branch; build Collection Manager UI; build Collection Inspector UI; wire new API endpoints. |

---

## Task 1: Add Ollama GPU Unload Helper

**Files:**
- Modify: `core/agent_swarm.py`

- [ ] **Step 1: Add unload helper next to `OllamaLLMClient`**

Add the following function near the top of `core/agent_swarm.py` (after imports):

```python
def ollama_unload_model(model: str, host: str = "http://localhost:11434") -> None:
    """Ask Ollama to unload a model from GPU memory immediately."""
    import requests
    try:
        requests.post(
            f"{host}/api/generate",
            json={"model": model, "prompt": "", "stream": False, "keep_alive": 0},
            timeout=30,
        )
        print(f"[OLLAMA] unload request sent for {model}")
    except Exception as e:
        print(f"[OLLAMA] unload request failed: {e}")
```

- [ ] **Step 2: Commit**

```bash
git add core/agent_swarm.py
git commit -m "feat: add ollama_unload_model helper"
```

---

## Task 2: Release GPU After Analysis

**Files:**
- Modify: `api/server.py`

- [ ] **Step 1: Import the helper**

Add an import near the existing lazy imports:

```python
try:
    from core.agent_swarm import ollama_unload_model as _ollama_unload_model
except ImportError:
    _ollama_unload_model = None
```

- [ ] **Step 2: Wrap analysis call with unload**

In the `/api/v1/analyse/disclosure` endpoint, replace:

```python
        result = swarm.analyse_disclosure(full_text, extra_collections=extra_collections)
```

with:

```python
        try:
            result = swarm.analyse_disclosure(full_text, extra_collections=extra_collections)
        finally:
            # Release GPU memory as soon as analysis finishes.
            try:
                model = getattr(engine, "llm_model", os.getenv("LLM_MODEL", "deepseek-r1"))
                if _ollama_unload_model is not None:
                    await asyncio.to_thread(_ollama_unload_model, model)
            except Exception:
                pass
```

- [ ] **Step 3: Commit**

```bash
git add api/server.py
git commit -m "feat: unload ollama model after disclosure analysis"
```

---

## Task 3: Add Analysis Concurrency Guard

**Files:**
- Modify: `api/server.py`

- [ ] **Step 1: Add a module-level semaphore**

Near `rag_engine = None` add:

```python
_analysis_semaphore = asyncio.Semaphore(1)
```

- [ ] **Step 2: Guard the analysis endpoint**

Wrap the body of `analyse_disclosure` with:

```python
    async with _analysis_semaphore:
        # existing endpoint body from auth check to return
```

Keep dependency injection outside the semaphore if possible, but it is acceptable to wrap the whole function body.

- [ ] **Step 3: Commit**

```bash
git add api/server.py
git commit -m "feat: limit analysis to one concurrent run to keep auth responsive"
```

---

## Task 4: Add Collection Helpers in RAG Engine

**Files:**
- Modify: `core/rag_engine.py`

- [ ] **Step 1: Add helper methods to NZLegalRAG**

Add after `get_database_stats`:

```python
    def list_all_collections(self) -> List[Dict[str, Any]]:
        """Return every collection in ChromaDB, including user-created ones."""
        result = []
        try:
            for coll in self.client.list_collections():
                name = getattr(coll, "name", str(coll))
                count = 0
                try:
                    count = self.client.get_collection(name).count()
                except Exception:
                    pass
                result.append({
                    "name": name,
                    "description": self.COLLECTIONS.get(name, ""),
                    "document_count": count,
                })
        except Exception as e:
            print(f"[list_all_collections] error: {e}")
        return sorted(result, key=lambda x: x["name"])

    def create_collection(self, name: str, description: str = "") -> None:
        """Create a new empty ChromaDB collection."""
        if name in self.collections:
            return
        try:
            self.collections[name] = self.client.create_collection(
                name=name,
                metadata={"description": description or f"Collection for {name}"},
            )
        except Exception:
            self.collections[name] = self.client.get_collection(name)

    def delete_collection(self, name: str) -> None:
        """Delete a ChromaDB collection."""
        self.client.delete_collection(name=name)
        self.collections.pop(name, None)

    def inspect_collection(self, name: str, offset: int = 0, limit: int = 20) -> Dict[str, Any]:
        """Return paginated chunks and metadata for a collection."""
        coll = self.client.get_collection(name)
        total = coll.count()
        data = coll.get(
            include=["documents", "metadatas"],
            offset=max(0, offset),
            limit=max(1, min(limit, 100)),
        )
        items = []
        for i, doc_id in enumerate(data.get("ids", [])):
            meta = data.get("metadatas", [])[i] if i < len(data.get("metadatas", [])) else {}
            items.append({
                "id": doc_id,
                "document": data.get("documents", [])[i] if i < len(data.get("documents", [])) else "",
                "metadata": meta,
            })
        # Unique source documents
        sources = set()
        for m in data.get("metadatas", []):
            src = m.get("source") or m.get("filename") or m.get("title") or "unknown"
            sources.add(src)
        return {
            "name": name,
            "total": total,
            "offset": offset,
            "limit": limit,
            "items": items,
            "unique_sources": sorted(sources),
        }
```

- [ ] **Step 2: Commit**

```bash
git add core/rag_engine.py
git commit -m "feat: add collection CRUD and inspect helpers"
```

---

## Task 5: Add Collection CRUD/Inspect Endpoints

**Files:**
- Modify: `api/server.py`

- [ ] **Step 1: Update collection list endpoint**

Replace the body of `list_collections` (`@app.get("/api/v1/collections")`) with:

```python
@app.get("/api/v1/collections")
def list_collections():
    engine = get_rag_engine()
    if engine is None:
        return {"collections": []}
    return {"collections": engine.list_all_collections()}
```

- [ ] **Step 2: Add admin collection endpoints**

Add after `list_collections`:

```python
SYSTEM_COLLECTIONS = {"nz_legislation", "nz_case_law", "nz_police_manual", "legal_research"}


def _sanitize_collection_name(name: str) -> str:
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9_-]", "-", name)
    name = re.sub(r"^-+|-+$", "", name)
    return name


@app.post("/api/v1/admin/collections/{name}")
def create_collection(
    name: str,
    description: str = "",
    tenant: Any = Depends(require_role(UserRole.ADMIN if UserRole else "admin", UserRole.STAFF if UserRole else "staff")),
):
    safe_name = _sanitize_collection_name(name)
    if not safe_name or len(safe_name) < 2:
        raise HTTPException(status_code=400, detail="Invalid collection name")
    engine = get_rag_engine()
    if engine is None:
        raise HTTPException(status_code=503, detail="RAG engine not available")
    try:
        engine.create_collection(safe_name, description=description)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"success": True, "name": safe_name, "message": f"Collection '{safe_name}' created"}


@app.delete("/api/v1/admin/collections/{name}")
def delete_collection(
    name: str,
    tenant: Any = Depends(require_role(UserRole.ADMIN if UserRole else "admin")),
):
    if name in SYSTEM_COLLECTIONS:
        raise HTTPException(status_code=403, detail="Cannot delete system collection")
    engine = get_rag_engine()
    if engine is None:
        raise HTTPException(status_code=503, detail="RAG engine not available")
    try:
        engine.delete_collection(name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"success": True, "name": name, "message": f"Collection '{name}' deleted"}


@app.get("/api/v1/admin/collections/{name}/inspect")
def inspect_collection(
    name: str,
    offset: int = 0,
    limit: int = 20,
    tenant: Any = Depends(require_role(UserRole.ADMIN if UserRole else "admin", UserRole.STAFF if UserRole else "staff")),
):
    engine = get_rag_engine()
    if engine is None:
        raise HTTPException(status_code=503, detail="RAG engine not available")
    try:
        return engine.inspect_collection(name, offset=offset, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

- [ ] **Step 3: Update admin stats to list all collections**

Replace the collection-count loop in `get_admin_stats` with:

```python
    if engine is not None:
        for col in engine.list_all_collections():
            collections.append(col)
            total_docs += col.get("document_count", 0)
```

- [ ] **Step 4: Commit**

```bash
git add api/server.py
git commit -m "feat: admin collection create/delete/inspect endpoints"
```

---

## Task 6: Fix Sidebar and Restore Upload Page

**Files:**
- Modify: `web/streamlit_app.py`

- [ ] **Step 1: Fix syntax in `show_sidebar()`**

Replace the admin/staff `pages` lists so they include commas:

```python
        if role == "admin":
            pages = [
                "Search",
                "Upload",
                "Defence Analysis",
                "Collection Manager",
                "Admin Panel",
            ]
        elif role in ["staff", "adminstaff"]:
            pages = [
                "Search",
                "Upload",
                "Defence Analysis",
                "Collection Manager",
            ]
```

- [ ] **Step 2: Add Upload branch in `main()`**

Update the dispatch block:

```python
    if page == "Home":
        show_home()
    elif page == "Upload":
        show_upload()
    elif page == "Collection Manager":
        show_collection_manager()
    elif page == "Search":
        show_search()
    elif page == "Defence Analysis":
        show_defence_analysis()
    elif page == "Admin Panel":
        show_adminpanel()
```

- [ ] **Step 3: Simplify Upload page for permanent uploads only**

In `show_upload()`, for privileged users remove the "Temporary session" radio option. Replace the destination/collection radios with:

```python
        st.markdown("### Permanent Upload")
        st.markdown(
            "<div class='aegis-note'>Upload documents into the permanent Chroma database. "
            "Choose whether to create a new collection or append to an existing one.</div>",
            unsafe_allow_html=True,
        )

        collectionmode = st.radio(
            "Collection action",
            ["Create new collection", "Add to existing collection"],
            horizontal=True,
            key="collectionmode",
        )
```

Then always use `targetcollection = collectionname` (no temp branch) and remove the auto-redirect to Defence Analysis. Keep the success message on the Upload page.

- [ ] **Step 4: Commit**

```bash
git add web/streamlit_app.py
git commit -m "fix: restore Upload page for permanent collection uploads only"
```

---

## Task 7: Build Collection Manager UI

**Files:**
- Modify: `web/streamlit_app.py`

- [ ] **Step 1: Replace `show_collection_manager()` body**

```python
def show_collection_manager() -> None:
    """Admin/staff collection management page."""
    render_brand_header()
    st.markdown("<div class='aegis-panel'>", unsafe_allow_html=True)
    st.markdown("### Collection Manager")

    role = str(st.session_state.get("role", "user")).lower().strip() or "user"
    is_admin = role == "admin"

    # Refresh collections
    collections = get_existing_collections()

    # Create new collection
    with st.expander("➕ Create new collection", expanded=False):
        new_name = st.text_input("Collection name", key="cm_new_name", placeholder="e.g. police-disclosure-june-2026")
        new_desc = st.text_input("Description (optional)", key="cm_new_desc", placeholder="Brief description")
        if st.button("Create collection", key="cm_create_btn"):
            if not new_name.strip():
                st.warning("Enter a collection name.")
            else:
                result = api_call(
                    f"/api/v1/admin/collections/{new_name.strip()}",
                    data={"description": new_desc.strip()},
                    method="POST",
                    apikey=st.session_state.get("apikey"),
                    sessionid=st.session_state.get("sessionid"),
                )
                if result and result.get("success"):
                    st.success(result.get("message"))
                    st.rerun()
                else:
                    st.error("Failed to create collection.")

    # List existing collections
    if not collections:
        st.info("No collections found.")
    else:
        st.markdown(f"**{len(collections)} collection(s) found**")
        for col in collections:
            c1, c2, c3 = st.columns([4, 1, 1])
            with c1:
                st.markdown(f"- **{col}**")
            with c2:
                if st.button("Inspect", key=f"cm_inspect_{col}"):
                    st.session_state["inspect_collection"] = col
                    st.session_state["inspect_offset"] = 0
                    st.session_state["page"] = "Collection Inspector"
                    st.rerun()
            with c3:
                if is_admin and st.button("Delete", key=f"cm_delete_{col}"):
                    st.session_state["confirm_delete_collection"] = col

    # Confirmation dialog
    if st.session_state.get("confirm_delete_collection"):
        col = st.session_state["confirm_delete_collection"]
        st.warning(f"Are you sure you want to delete collection '{col}'? This cannot be undone.")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Yes, delete", key="cm_confirm_delete"):
                result = api_call(
                    f"/api/v1/admin/collections/{col}",
                    method="DELETE",
                    apikey=st.session_state.get("apikey"),
                    sessionid=st.session_state.get("sessionid"),
                )
                if result and result.get("success"):
                    st.success(result.get("message"))
                    st.session_state.pop("confirm_delete_collection", None)
                    st.rerun()
                else:
                    st.error("Failed to delete collection.")
        with c2:
            if st.button("Cancel", key="cm_cancel_delete"):
                st.session_state.pop("confirm_delete_collection", None)
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
```

- [ ] **Step 2: Add Collection Inspector to sidebar pages**

Add `"Collection Inspector"` to the admin/staff `pages` lists in `show_sidebar()`.

- [ ] **Step 3: Commit**

```bash
git add web/streamlit_app.py
git commit -m "feat: collection manager create/delete/inspect UI"
```

---

## Task 8: Build Collection Inspector UI

**Files:**
- Modify: `web/streamlit_app.py`

- [ ] **Step 1: Add `show_collection_inspector()` function**

Add before `show_adminpanel()`:

```python
def show_collection_inspector() -> None:
    """Browse chunks inside a selected collection."""
    render_brand_header()
    st.markdown("<div class='aegis-panel'>", unsafe_allow_html=True)
    st.markdown("### Collection Inspector")

    collections = get_existing_collections()
    current = st.session_state.get("inspect_collection")
    selected = st.selectbox("Select collection", options=collections, index=collections.index(current) if current in collections else 0, key="ci_select")
    if selected != current:
        st.session_state["inspect_collection"] = selected
        st.session_state["inspect_offset"] = 0
        st.rerun()

    offset = st.session_state.get("inspect_offset", 0)
    limit = st.selectbox("Chunks per page", [10, 20, 50, 100], index=1, key="ci_limit")

    if st.button("Load chunks", key="ci_load"):
        result = api_call(
            f"/api/v1/admin/collections/{selected}/inspect",
            data={"offset": offset, "limit": limit},
            method="GET",
            apikey=st.session_state.get("apikey"),
            sessionid=st.session_state.get("sessionid"),
        )
        if result:
            st.session_state["inspect_result"] = result

    result = st.session_state.get("inspect_result")
    if result and result.get("name") == selected:
        st.markdown(f"**{result.get('total', 0)} total chunks** — showing {len(result.get('items', []))}")
        if result.get("unique_sources"):
            st.caption("Sources: " + ", ".join(str(s) for s in result["unique_sources"]))

        for i, item in enumerate(result.get("items", []), start=offset + 1):
            meta = item.get("metadata", {}) or {}
            source = meta.get("filename") or meta.get("source") or meta.get("title") or "unknown"
            page = meta.get("page") or meta.get("pagenumber") or meta.get("page_number")
            header = f"Chunk {i}: {source}"
            if page:
                header += f" (page {page})"
            with st.expander(header):
                st.caption(f"ID: {item.get('id', 'N/A')}")
                st.json(meta)
                st.markdown(item.get("document", "")[:2000])

        # Pagination
        total = result.get("total", 0)
        col1, col2, col3 = st.columns(3)
        with col1:
            if offset > 0 and st.button("← Previous"):
                st.session_state["inspect_offset"] = max(0, offset - limit)
                st.rerun()
        with col2:
            st.write(f"Offset {offset}")
        with col3:
            if offset + limit < total and st.button("Next →"):
                st.session_state["inspect_offset"] = offset + limit
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
```

- [ ] **Step 2: Add dispatch branch**

In `main()`:

```python
    elif page == "Collection Inspector":
        show_collection_inspector()
```

- [ ] **Step 3: Commit**

```bash
git add web/streamlit_app.py
git commit -m "feat: collection inspector UI"
```

---

## Task 9: Convert Auth Endpoints to Async

**Files:**
- Modify: `api/server.py`

- [ ] **Step 1: Make demo auth and login async**

Convert the following endpoint functions to `async def` and wrap any blocking calls in `asyncio.to_thread`:

- `demo_start`
- `demo_verify`
- `demo_logout`
- `/api/v1/login`
- `get_my_tenant`

For example, `demo_start` becomes:

```python
@app.post("/auth/demo/start", response_model=DemoStartResponse)
async def demo_start(request: DemoStartRequest):
    challenges, sessions = await asyncio.to_thread(purge_expired_demo_state)
    ...
    await asyncio.to_thread(_save_demo_state, challenges, sessions)
```

Similarly wrap `_save_demo_state` and `_load_demo_state` calls.

- [ ] **Step 2: Commit**

```bash
git add api/server.py
git commit -m "refactor: make auth endpoints async to avoid thread-pool starvation"
```

---

## Task 10: Verification

**Files:**
- All modified files

- [ ] **Step 1: Syntax check**

```bash
python -m py_compile api/server.py web/streamlit_app.py core/rag_engine.py core/agent_swarm.py
```

Expected: no output (success).

- [ ] **Step 2: Run existing pipeline tests**

```bash
python test_pipeline.py
```

Expected: existing assertions pass (the stub path runs without Ollama).

- [ ] **Step 3: Manual checks**

1. Start API: `python -m api.server`
2. Start Streamlit: `streamlit run web/streamlit_app.py`
3. Log in as admin/staff and verify:
   - Upload page appears and works for permanent collections.
   - Collection Manager can create/delete collections.
   - Collection Inspector shows chunks and metadata.
4. Run Defence Analysis on a large disclosure and verify:
   - A second browser/session can still log in.
   - `nvidia-smi` shows VRAM dropping shortly after analysis completes.

- [ ] **Step 4: Commit any fixes**

---

## Spec Coverage Check

| Spec Requirement | Task(s) |
|---|---|
| GPU release after analysis | Task 1, Task 2 |
| Login concurrency during analysis | Task 3, Task 9 |
| Collection Manager add/remove | Task 4, Task 5, Task 7 |
| Dive into collections (inspector) | Task 4, Task 5, Task 8 |
| Upload in radio menu, permanent only | Task 6 |

## Placeholder Scan

No TBD/TODO placeholders. Every task includes exact file paths, code snippets, and commands.
