#!/usr/bin/env python3
"""
Reclassify documents from user_uploads into the correct collections
based on filename heuristics.

Usage:
    python tools/reclassify_uploads.py --dry-run   # Preview only
    python tools/reclassify_uploads.py --confirm   # Actually move documents
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import chromadb


def classify_by_filename(filename: str) -> str:
    """Classify a document based on its filename."""
    lower = filename.lower()
    
    # Legislation indicators
    legislation_keywords = [
        'act', 'regulation', 'statute', 'legislation', 'bill', 
        'amendment', 'ordinance', 'decree', 'law ', 'laws ', 'legal_code'
    ]
    for kw in legislation_keywords:
        if kw in lower:
            return 'nz_legislation'
    
    # Case law indicators
    case_keywords = [
        'r v ', 'r vs ', 'v ', 'case', 'judgment', 'court', 
        'nzsc', 'nzca', 'nzhc', 'nzdc', 'nzlr', 'crnz'
    ]
    for kw in case_keywords:
        if kw in lower:
            return 'nz_case_law'
    
    # Police manual indicators
    police_keywords = [
        'police', 'manual', 'procedure', 'protocol', 'operational',
        'tactical', 'investigation guide', 'custody', 'arrest '
    ]
    for kw in police_keywords:
        if kw in lower:
            return 'nz_police_manual'
    
    return 'user_uploads'


def main():
    parser = argparse.ArgumentParser(description="Reclassify uploaded documents")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without moving")
    parser.add_argument("--confirm", action="store_true", help="Confirm and execute moves")
    args = parser.parse_args()
    
    if not args.dry_run and not args.confirm:
        print("Usage:")
        print("  python tools/reclassify_uploads.py --dry-run   # Preview")
        print("  python tools/reclassify_uploads.py --confirm   # Execute")
        return
    
    db_path = "./chroma_db"
    client = chromadb.PersistentClient(path=db_path)
    
    try:
        source_coll = client.get_collection("user_uploads")
    except Exception as e:
        print(f"Error accessing user_uploads: {e}")
        return
    
    # Get all documents from user_uploads
    print("Fetching documents from user_uploads...")
    total = source_coll.count()
    print(f"Total documents in user_uploads: {total}")
    
    if total == 0:
        print("Nothing to reclassify.")
        return
    
    # Fetch in batches
    batch_size = 100
    moves = {}
    
    for offset in range(0, total, batch_size):
        results = source_coll.get(
            limit=batch_size,
            offset=offset,
            include=["documents", "metadatas", "embeddings"]
        )
        
        for i, doc_id in enumerate(results["ids"]):
            meta = results["metadatas"][i]
            filename = meta.get("source", "unknown")
            target = classify_by_filename(filename)
            
            if target != "user_uploads":
                if target not in moves:
                    moves[target] = []
                moves[target].append({
                    "id": doc_id,
                    "document": results["documents"][i],
                    "metadata": meta,
                    "embedding": results["embeddings"][i] if "embeddings" in results and results["embeddings"] is not None else None,
                    "filename": filename
                })
    
    if not moves:
        print("No documents matched classification heuristics.")
        print("Filenames did not contain legislation/case-law/police keywords.")
        return
    
    # Preview
    print(f"\n{'='*60}")
    print("RECLASSIFICATION PLAN")
    print(f"{'='*60}")
    
    for target, docs in moves.items():
        print(f"\n→ {target}: {len(docs)} documents")
        for d in docs[:5]:
            print(f"    • {d['filename']}")
        if len(docs) > 5:
            print(f"    ... and {len(docs) - 5} more")
    
    total_moves = sum(len(d) for d in moves.values())
    print(f"\nTotal documents to move: {total_moves}")
    
    if args.dry_run:
        print("\n(Dry run — no changes made)")
        print("Run with --confirm to execute.")
        return
    
    # Execute moves
    print(f"\n{'='*60}")
    print("EXECUTING MOVES...")
    print(f"{'='*60}")
    
    for target, docs in moves.items():
        print(f"\nMoving {len(docs)} documents to {target}...")
        
        try:
            target_coll = client.get_collection(target)
        except Exception:
            print(f"  Creating collection {target}...")
            target_coll = client.create_collection(
                name=target,
                metadata={"description": f"Collection for {target}"}
            )
        
        ids = []
        documents = []
        metadatas = []
        embeddings = []
        
        for d in docs:
            ids.append(d["id"])
            documents.append(d["document"])
            meta = dict(d["metadata"])
            meta["reclassified_from"] = "user_uploads"
            meta["reclassified_at"] = "2026-04-24"
            metadatas.append(meta)
            if d["embedding"] is not None:
                embeddings.append(d["embedding"])
        
        try:
            if embeddings and len(embeddings) == len(ids):
                target_coll.add(
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas,
                    embeddings=embeddings
                )
            else:
                target_coll.add(
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas
                )
            print(f"  ✓ Added {len(ids)} documents to {target}")
        except Exception as e:
            print(f"  ✗ Failed to add to {target}: {e}")
            continue
        
        # Delete from source
        try:
            source_coll.delete(ids=ids)
            print(f"  ✓ Deleted {len(ids)} documents from user_uploads")
        except Exception as e:
            print(f"  ✗ Failed to delete from user_uploads: {e}")
    
    print(f"\n{'='*60}")
    print("DONE")
    print(f"{'='*60}")
    
    # Show final stats
    for coll_name in ["user_uploads", "nz_legislation", "nz_case_law", "nz_police_manual"]:
        try:
            c = client.get_collection(coll_name)
            print(f"  {coll_name}: {c.count()} documents")
        except Exception:
            pass


if __name__ == "__main__":
    main()
