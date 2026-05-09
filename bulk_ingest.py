#!/usr/bin/env python3
"""
Bulk ingest script for RunPod ChromaDB.
Downloads JSON.gz exports and inserts directly into ChromaDB collections.
"""
import json
import gzip
import os
import sys
import time
import hashlib
import requests

# Vultr download URL base
VULTR_BASE = "http://69.30.85.149:9999"
CHROMA_PATH = "/workspace/nz_legal_rag/chroma_db"
OLLAMA_URL = "http://localhost:11434/api/embeddings"
MODEL = "nomic-embed-text:latest"
EMBEDDING_DIM = 768

def get_embedding(text: str) -> list:
    """Get embedding via Ollama."""
    try:
        r = requests.post(OLLAMA_URL, json={"model": MODEL, "prompt": text[:8000]}, timeout=60)
        r.raise_for_status()
        return r.json()["embedding"]
    except Exception as e:
        print(f"  Embedding error: {e}")
        return None

def download_file(url: str, local_path: str):
    """Download with progress."""
    print(f"Downloading {url} ...")
    r = requests.get(url, stream=True, timeout=120)
    r.raise_for_status()
    total = int(r.headers.get('content-length', 0))
    downloaded = 0
    chunk_size = 1024 * 1024
    with open(local_path, 'wb') as f:
        for chunk in r.iter_content(chunk_size=chunk_size):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded / total * 100
                    print(f"  {downloaded/1024/1024:.1f}MB / {total/1024/1024:.1f}MB ({pct:.0f}%)", end="\r")
    print(f"\nSaved to {local_path}")

def load_json_gz(path: str):
    """Load JSON.gz into list of dicts."""
    print(f"Loading {path} ...")
    with gzip.open(path, 'rt', encoding='utf-8') as f:
        data = json.load(f)
    if isinstance(data, dict):
        # Single document export
        return [data]
    return data

def ensure_collection(chroma_client, name: str):
    """Get or create collection with correct embedding dimension."""
    try:
        coll = chroma_client.get_collection(name=name)
        # Check dimension
        sample = coll.peek(limit=1)
        if sample and sample.get('embeddings') and sample['embeddings'][0]:
            dim = len(sample['embeddings'][0])
            if dim != EMBEDDING_DIM:
                print(f"  WARNING: Collection '{name}' has dim={dim}, expected {EMBEDDING_DIM}. Deleting and recreating...")
                chroma_client.delete_collection(name=name)
                return chroma_client.create_collection(name=name, metadata={"hnsw:space": "cosine"})
        return coll
    except Exception:
        print(f"  Creating collection: {name}")
        return chroma_client.create_collection(name=name, metadata={"hnsw:space": "cosine"})

def ingest_collection(chroma_client, collection_name: str, documents: list, batch_size: int = 50):
    """Ingest documents into ChromaDB collection."""
    coll = ensure_collection(chroma_client, collection_name)
    
    total = len(documents)
    print(f"Ingesting {total} documents into '{collection_name}' ...")
    
    success = 0
    failed = 0
    skipped = 0
    
    for i in range(0, total, batch_size):
        batch = documents[i:i+batch_size]
        ids = []
        texts = []
        metadatas = []
        embeddings = []
        
        for doc in batch:
            # Extract content
            content = doc.get("page_content", doc.get("content", doc.get("text", "")))
            if not content or not content.strip():
                skipped += 1
                continue
            
            # Generate ID
            doc_id = doc.get("id", doc.get("document_id", doc.get("chunk_id")))
            if not doc_id:
                doc_id = hashlib.md5(content[:500].encode()).hexdigest()
            
            # Ensure unique ID within batch
            base_id = doc_id
            counter = 1
            while doc_id in ids:
                doc_id = f"{base_id}_{counter}"
                counter += 1
            
            # Metadata
            meta = doc.get("metadata", {})
            if not isinstance(meta, dict):
                meta = {}
            
            # Add source info
            source = meta.get("source", meta.get("filename", meta.get("file_path", doc.get("source", "unknown"))))
            meta["source"] = source
            meta["ingest_batch"] = "bulk_2026_04_27"
            
            # Truncate content for embedding if needed
            embed_text = content[:8000]
            emb = get_embedding(embed_text)
            if emb is None:
                failed += 1
                continue
            
            ids.append(doc_id)
            texts.append(content)
            metadatas.append(meta)
            embeddings.append(emb)
        
        if ids:
            try:
                coll.add(ids=ids, documents=texts, metadatas=metadatas, embeddings=embeddings)
                success += len(ids)
            except Exception as e:
                print(f"  Batch add error: {e}")
                failed += len(ids)
        
        print(f"  Progress: {min(i+batch_size, total)}/{total} | success={success} failed={failed} skipped={skipped}")
        time.sleep(0.5)  # Rate limit
    
    print(f"Done. Total: {total}, Success: {success}, Failed: {failed}, Skipped: {skipped}")
    return success

def main():
    # Import chromadb here so we fail fast if not installed
    try:
        import chromadb
    except ImportError:
        print("ERROR: chromadb not installed. Run: pip install chromadb")
        sys.exit(1)
    
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    
    # Check current counts
    print("=" * 60)
    print("Current collections:")
    for name in client.list_collections():
        try:
            c = client.get_collection(name=name)
            count = c.count()
            print(f"  {name}: {count} documents")
        except Exception as e:
            print(f"  {name}: error - {e}")
    print("=" * 60)
    
    # Download files
    files = [
        ("nz_legal_unified_backup.json.gz", "nz_legal_unified"),
        ("legacy_documents.json.gz", "legacy_documents"),
    ]
    
    for filename, collection_name in files:
        local_path = f"/tmp/{filename}"
        url = f"{VULTR_BASE}/{filename}"
        
        if not os.path.exists(local_path):
            try:
                download_file(url, local_path)
            except Exception as e:
                print(f"ERROR downloading {filename}: {e}")
                continue
        else:
            print(f"Using cached {local_path}")
        
        # Load and ingest
        try:
            docs = load_json_gz(local_path)
            print(f"Loaded {len(docs)} documents")
            ingest_collection(client, collection_name, docs, batch_size=50)
        except Exception as e:
            print(f"ERROR ingesting {filename}: {e}")
            import traceback
            traceback.print_exc()
    
    # Final counts
    print("=" * 60)
    print("Final collections:")
    for name in client.list_collections():
        try:
            c = client.get_collection(name=name)
            count = c.count()
            print(f"  {name}: {count} documents")
        except Exception as e:
            print(f"  {name}: error - {e}")
    print("=" * 60)
    print("Bulk ingest complete!")

if __name__ == "__main__":
    main()
