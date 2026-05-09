#!/usr/bin/env python3
"""
Batch Re-categorization - Simplified Version
Processes documents in efficient batches
"""

import chromadb
import re
from collections import defaultdict
from datetime import datetime
import time

CHROMA_PATH = "./chroma_db"

def quick_categorize(metadata, document):
    """Quick content-based categorization"""
    source = metadata.get('source', '').upper()
    doc_upper = document[:1000].upper()
    
    # Case law patterns (most common)
    if re.search(r'\[\d{4}\].*(NZLR|NZSC|NZCA|NZHC)', doc_upper):
        return 'case_law'
    if 'R V ' in doc_upper or 'R VS ' in doc_upper:
        return 'case_law'
    if 'JUDGMENT' in doc_upper and 'COURT' in doc_upper:
        return 'case_law'
    
    # Legislation patterns
    if re.search(r'(ACT|BILL)\s+\d{4}', source):
        return 'legislation'
    if re.search(r'(CRIMES|MISUSE OF DRUGS|EVIDENCE|SEARCH AND SURVEILLANCE)\s+ACT', doc_upper):
        return 'legislation'
    
    # Police manual
    if 'POLICE MANUAL' in source or 'POLICE MANUAL' in doc_upper:
        return 'police_manual'
    
    return 'uncategorized'

def process_batch():
    """Process remaining documents"""
    print("=" * 70)
    print("BATCH RE-CATEGORIZATION")
    print("=" * 70)
    
    client = chromadb.PersistentClient(CHROMA_PATH)
    
    # Get source collections
    sources = ['uncategorized', 'nz_legal_unified']
    targets = {
        'case_law': client.get_or_create_collection('nz_case_law'),
        'legislation': client.get_or_create_collection('nz_legislation'),
        'police_manual': client.get_or_create_collection('nz_police_manual'),
        'uncategorized': client.get_or_create_collection('uncategorized_new'),
    }
    
    total_moved = 0
    
    for source_name in sources:
        try:
            source = client.get_collection(source_name)
        except:
            print(f"Collection {source_name} not found, skipping")
            continue
        
        count = source.count()
        if count == 0:
            print(f"\n{source_name}: empty, skipping")
            continue
        
        print(f"\nProcessing {source_name}: {count} documents")
        
        # Get all documents
        results = source.get()
        
        # Sort by category
        by_category = defaultdict(list)
        for doc_id, doc, meta in zip(results['ids'], results['documents'], results['metadatas']):
            cat = quick_categorize(meta, doc)
            by_category[cat].append({
                'id': doc_id,
                'document': doc,
                'metadata': {**meta, 'category': cat, 'recategorized_at': datetime.now().isoformat()}
            })
        
        # Show distribution
        print("  Distribution:")
        for cat, docs in sorted(by_category.items(), key=lambda x: len(x[1]), reverse=True):
            print(f"    • {cat}: {len(docs)}")
        
        # Move to targets
        for cat, docs in by_category.items():
            if not docs:
                continue
            
            target = targets[cat]
            
            # Add in batches of 100
            for i in range(0, len(docs), 100):
                batch = docs[i:i+100]
                target.add(
                    ids=[d['id'] for d in batch],
                    documents=[d['document'] for d in batch],
                    metadatas=[d['metadata'] for d in batch]
                )
            
            print(f"  → Moved {len(docs)} to {cat}")
            total_moved += len(docs)
        
        # Delete source collection
        print(f"  Deleting {source_name}...")
        client.delete_collection(source_name)
        print(f"  ✓ {source_name} deleted")
    
    print("\n" + "=" * 70)
    print(f"✓ COMPLETE: Moved {total_moved} documents")
    print("=" * 70)
    
    # Show final state
    print("\nFinal collections:")
    for col in sorted(client.list_collections(), key=lambda x: x.name):
        print(f"  {col.name}: {col.count()}")

if __name__ == "__main__":
    process_batch()
