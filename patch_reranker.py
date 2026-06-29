#!/usr/bin/env python3
# Patch server.py to add reranker and citation grounding
import sys
from pathlib import Path

SERVER_PATH = Path("/workspace/nz_legal_rag/api/server.py")
BACKUP = Path("/workspace/nz_legal_rag/api/server.py.bak.reranker")

def patch():
    if not SERVER_PATH.exists():
        print(f"ERROR: {SERVER_PATH} not found")
        sys.exit(1)
    
    BACKUP.write_text(SERVER_PATH.read_text(), encoding="utf-8")
    print(f"Backup: {BACKUP}")
    
    content = SERVER_PATH.read_text(encoding="utf-8")
    
    # 1. Add reranker import
    old = "UserRole = None\n\ntry:\n    from core.file_parser"
    new = "UserRole = None\nReranker = None\n\ntry:\n    from sentence_transformers import CrossEncoder\n    Reranker = CrossEncoder\nexcept ImportError:\n    pass\n\ntry:\n    from core.file_parser"
    if old in content:
        content = content.replace(old, new)
        print("Added reranker import")
    
    # 2. Add reranker global
    old = "rag_engine: Optional[Any] = None\ntenant_manager: Optional[Any] = None"
    new = "rag_engine: Optional[Any] = None\ntenant_manager: Optional[Any] = None\nreranker_model: Optional[Any] = None"
    if old in content:
        content = content.replace(old, new)
        print("Added reranker global")
    
    # 3. Add get_reranker function
    old = "    return rag_engine\n\n\ndef _clean_ollama_options"
    new = "    return rag_engine\n\n\ndef get_reranker() -> Optional[Any]:\n    global reranker_model\n    if reranker_model is None and Reranker is not None:\n        model_name = os.getenv(\"RERANKER_MODEL\", \"BAAI/bge-reranker-base\")\n        try:\n            reranker_model = Reranker(model_name)\n            print(f\"Loaded reranker: {model_name}\")\n        except Exception as e:\n            print(f\"Could not load reranker {model_name}: {e}\")\n            reranker_model = None\n    return reranker_model\n\n\ndef _clean_ollama_options"
    if old in content:
        content = content.replace(old, new)
        print("Added get_reranker function")
    
    # 4. Increase retrieval top_k
    old = "        top_k=min(MAX_ANALYSIS_SOURCES, 6),"
    new = "        top_k=min(MAX_ANALYSIS_SOURCES * 3, 15),  # Retrieve more for reranking"
    if old in content:
        content = content.replace(old, new)
        print("Increased top_k for reranking")
    
    # 5. Add reranker call after search
    old = "    retrieved = engine.search(\n        query=request.query,\n        collections=collections,\n        filters=None,\n        top_k=min(MAX_ANALYSIS_SOURCES * 3, 15),  # Retrieve more for reranking\n    )\n\n    compact_context = _build_compact_context(retrieved)"
    new = "    retrieved = engine.search(\n        query=request.query,\n        collections=collections,\n        filters=None,\n        top_k=min(MAX_ANALYSIS_SOURCES * 3, 15),  # Retrieve more for reranking\n    )\n\n    # RERANKER: Re-rank retrieved documents for better relevance\n    reranker = get_reranker()\n    if reranker is not None and len(retrieved) > 1:\n        try:\n            pairs = [[request.query, getattr(doc, \"document\", str(doc))] for doc in retrieved]\n            scores = reranker.predict(pairs)\n            scored = list(zip(scores, retrieved))\n            scored.sort(key=lambda x: x[0], reverse=True)\n            retrieved = [doc for _, doc in scored]\n        except Exception as e:\n            print(f\"Reranker failed: {e}\")\n\n    compact_context = _build_compact_context(retrieved)"
    if old in content:
        content = content.replace(old, new)
        print("Added reranker to analyze endpoint")
    else:
        print("WARNING: Could not find search block")
    
    # 6. Add citation grounding
    old = "    full_query = request.query\n    if context_parts:\n        full_query = request.query + f\\\"\\n\\nContext:\\n{joined_context}\\\""
    new = "    full_query = request.query\n    if context_parts:\n        grounding = (\n            \"\\n\\nINSTRUCTIONS:\\n\"\n            \"1. Answer based ONLY on the provided sources above.\\n\"\n            \"2. Cite every claim as [Source N] where N matches the source number.\\n\"\n            \"3. If sources are insufficient, say so explicitly.\\n\"\n            \"4. Do not cite cases or statutes not present in the sources.\"\n        )\n        full_query = request.query + f\\\"\\n\\nContext:\\n{joined_context}{grounding}\\\""
    if old in content:
        content = content.replace(old, new)
        print("Added citation grounding")
    else:
        print("WARNING: Could not find query block")
    
    SERVER_PATH.write_text(content, encoding="utf-8")
    print(f"\nSUCCESS: Patched {SERVER_PATH}")
    print("Install: pip install sentence-transformers")
    print("Download: python -c 'from sentence_transformers import CrossEncoder; CrossEncoder(\"BAAI/bge-reranker-base\")'")

if __name__ == "__main__":
    patch()
