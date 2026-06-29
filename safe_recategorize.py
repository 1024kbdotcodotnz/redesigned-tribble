#!/usr/bin/env python3
"""
Safe Incremental Re-categorization Script
Processes documents in small batches with backups and verification
"""

import chromadb
import re
import json
import shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path
import time

CHROMA_PATH = "/workspace/chroma_db_fresh"
CHECKPOINT_FILE = "./recategorize_checkpoint.json"
BATCH_SIZE = 500
MAX_DOCS_PER_RUN = 2000  # Process max 2000 docs per run to avoid timeouts

def create_backup():
    """Create a timestamped backup of the database"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = f"./backups/chroma_db_backup_{timestamp}"
    
    print(f"📦 Creating backup: {backup_dir}")
    shutil.copytree(CHROMA_PATH, backup_dir)
    print(f"✓ Backup created")
    return backup_dir

def load_checkpoint():
    """Load progress checkpoint"""
    if Path(CHECKPOINT_FILE).exists():
        with open(CHECKPOINT_FILE) as f:
            return json.load(f)
    return {
        'processed_collections': {},
        'total_moved': 0,
        'last_backup': None
    }

def save_checkpoint(checkpoint):
    """Save progress checkpoint"""
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump(checkpoint, f, indent=2)

def quick_categorize(document):
    """Quick content-based categorization"""
    doc_upper = document[:800].upper()
    
    # Case law (most common)
    if re.search(r'\[\d{4}\].*(NZLR|NZSC|NZCA|NZHC)', doc_upper):
        return 'case_law'
    if 'R V ' in doc_upper or 'R VS ' in doc_upper:
        return 'case_law'
    if 'JUDGMENT' in doc_upper and 'COURT' in doc_upper:
        return 'case_law'
    if 'APPELLANT' in doc_upper:
        return 'case_law'
    
    # Legislation
    if re.search(r'(CRIMES|MISUSE OF DRUGS|EVIDENCE|SEARCH AND SURVEILLANCE|BILL OF RIGHTS)\s+ACT', doc_upper):
        return 'legislation'
    if 'SECTION' in doc_upper and re.search(r'ACT\s+\d{4}', doc_upper):
        return 'legislation'
    
    # Police manual
    if 'POLICE MANUAL' in doc_upper or 'POLICE POWERS' in doc_upper:
        return 'police_manual'
    
    # Legal research
    if any(x in doc_upper for x in ['ANALYSIS', 'RESEARCH NOTE', 'OVERVIEW']):
        return 'legal_research'
    
    return 'uncategorized'

def process_collection_safely(client, source_name, targets, checkpoint):
    """Process a collection in small batches with checkpointing"""
    
    print(f"\n{'='*70}")
    print(f"Processing: {source_name}")
    print('='*70)
    
    try:
        source = client.get_collection(source_name)
    except:
        print(f"Collection {source_name} not found or already processed")
        return 0
    
    total = source.count()
    if total == 0:
        print("Collection is empty")
        return 0
    
    # Check if already processed
    if checkpoint['processed_collections'].get(source_name, {}).get('completed'):
        print(f"✓ Already processed ({total} docs)")
        return 0
    
    # Get progress
    processed = checkpoint['processed_collections'].get(source_name, {}).get('offset', 0)
    print(f"Total: {total} documents")
    print(f"Already processed: {processed}")
    print(f"Remaining: {total - processed}")
    
    if processed >= total:
        print("✓ All documents processed")
        checkpoint['processed_collections'][source_name] = {'completed': True, 'total': total}
        save_checkpoint(checkpoint)
        return 0
    
    # Limit this run
    to_process = min(BATCH_SIZE, total - processed, MAX_DOCS_PER_RUN)
    print(f"\nProcessing batch: {to_process} documents")
    
    # Get batch
    results = source.get(limit=to_process, offset=processed)
    
    # Categorize
    by_category = defaultdict(list)
    for doc_id, doc, meta in zip(results['ids'], results['documents'], results['metadatas']):
        cat = quick_categorize(doc)
        by_category[cat].append({
            'id': doc_id,
            'document': doc,
            'metadata': {
                **meta,
                'category': cat,
                'recategorized_at': datetime.now().isoformat(),
                'original_collection': source_name
            }
        })
    
    # Show distribution
    print("\nDistribution:")
    for cat, docs in sorted(by_category.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"  • {cat}: {len(docs)}")
    
    # Move to targets
    total_moved = 0
    print("\nMoving documents...")
    for cat, docs in by_category.items():
        if not docs:
            continue
        
        target = targets.get(cat)
        if not target:
            print(f"  ⚠ No target for {cat}, skipping {len(docs)} docs")
            continue
        
        # Add in smaller sub-batches
        for i in range(0, len(docs), 100):
            batch = docs[i:i+100]
            try:
                target.add(
                    ids=[d['id'] for d in batch],
                    documents=[d['document'] for d in batch],
                    metadatas=[d['metadata'] for d in batch]
                )
            except Exception as e:
                print(f"  ❌ Error adding batch: {e}")
                return 0
        
        print(f"  ✓ Moved {len(docs)} to {cat}")
        total_moved += len(docs)
    
    # Update checkpoint
    new_processed = processed + to_process
    checkpoint['processed_collections'][source_name] = {
        'offset': new_processed,
        'total': total,
        'completed': new_processed >= total
    }
    checkpoint['total_moved'] += total_moved
    save_checkpoint(checkpoint)
    
    print(f"\n✓ Batch complete: {new_processed}/{total} processed")
    
    if new_processed >= total:
        print(f"\nDeleting source collection: {source_name}")
        try:
            client.delete_collection(source_name)
            print("  ✓ Deleted")
        except Exception as e:
            print(f"  ⚠ Could not delete: {e}")
    
    return total_moved

def main():
    """Main incremental re-categorization function"""
    print("=" * 70)
    print("SAFE INCREMENTAL RE-CATEGORIZATION")
    print("=" * 70)
    print(f"\nBatch size: {BATCH_SIZE}")
    print(f"Max per run: {MAX_DOCS_PER_RUN}")
    print(f"Checkpoint file: {CHECKPOINT_FILE}")
    
    # Create backup
    backup_path = create_backup()
    
    # Load checkpoint
    checkpoint = load_checkpoint()
    checkpoint['last_backup'] = backup_path
    save_checkpoint(checkpoint)
    
    print(f"\n✓ Checkpoint loaded")
    print(f"  Total previously moved: {checkpoint['total_moved']}")
    print(f"  Completed collections: {list(checkpoint['processed_collections'].keys())}")
    
    # Connect to database
    client = chromadb.PersistentClient(CHROMA_PATH)
    
    # Create/get target collections
    targets = {
        'case_law': client.get_or_create_collection('nz_case_law'),
        'legislation': client.get_or_create_collection('nz_legislation'),
        'police_manual': client.get_or_create_collection('nz_police_manual'),
        'legal_research': client.get_or_create_collection('legal_research'),
        'uncategorized': client.get_or_create_collection('uncategorized_new'),
    }
    
    # Collections to process (in order)
    sources = ['uncategorized', 'nz_legal_unified']
    
    total_this_run = 0
    for source_name in sources:
        moved = process_collection_safely(client, source_name, targets, checkpoint)
        total_this_run += moved
        
        if total_this_run >= MAX_DOCS_PER_RUN:
            print(f"\n⏸️ Reached max per run limit ({MAX_DOCS_PER_RUN})")
            break
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"\nThis run: {total_this_run} documents moved")
    print(f"Total moved: {checkpoint['total_moved']} documents")
    
    print("\nCollection status:")
    for col in sorted(client.list_collections(), key=lambda x: x.name):
        print(f"  {col.name}: {col.count()}")
    
    # Check if complete
    all_complete = all(
        checkpoint['processed_collections'].get(s, {}).get('completed', False)
        for s in sources
    )
    
    if all_complete:
        print("\n✅ ALL COLLECTIONS PROCESSED!")
        print("\nCleaning up...")
        Path(CHECKPOINT_FILE).unlink(missing_ok=True)
        print("  ✓ Checkpoint file removed")
    else:
        remaining = sum(
            1 for s in sources 
            if not checkpoint['processed_collections'].get(s, {}).get('completed', False)
        )
        print(f"\n⏳ {remaining} collections still need processing")
        print(f"   Run this script again to continue")
    
    print("\nBackup location:", backup_path)

if __name__ == "__main__":
    main()
