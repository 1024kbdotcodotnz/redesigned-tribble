#!/usr/bin/env python3
"""Finish processing nz_legal_unified collection"""
import chromadb
import re
from collections import defaultdict
from datetime import datetime

CHROMA_PATH = "/workspace/chroma_db_fresh"

def categorize(doc, meta):
    doc_upper = doc[:1000].upper()
    
    # Case law (most common)
    if re.search(r'\[\d{4}\].*(NZLR|NZSC|NZCA|NZHC)', doc_upper):
        return 'case_law'
    if 'R V ' in doc_upper or 'JUDGMENT' in doc_upper:
        return 'case_law'
    
    # Legislation
    if re.search(r'(CRIMES|MISUSE OF DRUGS|EVIDENCE|ACT)\s+\d{4}', doc_upper):
        return 'legislation'
    
    # Police manual
    if 'POLICE MANUAL' in doc_upper:
        return 'police_manual'
    
    return 'uncategorized'

def main():
    print("Processing nz_legal_unified...")
    client = chromadb.PersistentClient(CHROMA_PATH)
    
    try:
        source = client.get_collection('nz_legal_unified')
    except:
        print("nz_legal_unified not found - already processed!")
        return
    
    count = source.count()
    print(f"Documents: {count}")
    
    targets = {
        'case_law': client.get_or_create_collection('nz_case_law'),
        'legislation': client.get_or_create_collection('nz_legislation'),
        'police_manual': client.get_or_create_collection('nz_police_manual'),
        'uncategorized': client.get_or_create_collection('uncategorized_new'),
    }
    
    # Process in batches
    batch_size = 500
    offset = 0
    total_moved = 0
    
    while offset < count:
        print(f"  Processing {offset}-{min(offset+batch_size, count)}...")
        results = source.get(limit=batch_size, offset=offset)
        
        by_cat = defaultdict(list)
        for doc_id, doc, meta in zip(results['ids'], results['documents'], results['metadatas']):
            cat = categorize(doc, meta)
            by_cat[cat].append({
                'id': doc_id,
                'document': doc,
                'metadata': {**meta, 'category': cat, 'recategorized': datetime.now().isoformat()}
            })
        
        # Move to targets
        for cat, docs in by_cat.items():
            if docs:
                targets[cat].add(
                    ids=[d['id'] for d in docs],
                    documents=[d['document'] for d in docs],
                    metadatas=[d['metadata'] for d in docs]
                )
                total_moved += len(docs)
        
        offset += batch_size
    
    # Delete source
    print("Deleting nz_legal_unified...")
    client.delete_collection('nz_legal_unified')
    
    print(f"✓ Done! Moved {total_moved} documents")
    
    # Show final
    print("\nFinal state:")
    for col in sorted(client.list_collections(), key=lambda x: x.name):
        print(f"  {col.name}: {col.count()}")

if __name__ == "__main__":
    main()
