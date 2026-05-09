#!/usr/bin/env python3
"""
Smart Re-categorization Script
Properly categorizes documents based on source and content analysis
"""

import chromadb
import re
from collections import defaultdict
from datetime import datetime

CHROMA_PATH = "./chroma_db"

def determine_category(metadata, document):
    """
    Determine the correct category based on source and content analysis
    """
    source = metadata.get('source', '').upper()
    title = metadata.get('title', '').upper()
    source_collection = metadata.get('source_collection', '').upper()
    doc_upper = document[:2000].upper()
    
    # Priority 1: Source-based detection
    if 'NZ LEGISLATION' in source or 'NZ LEGISLATION' in source_collection:
        if re.search(r'(ACT|BILL)\s+\d{4}', source):
            return 'legislation'
        if 'ACT ' in doc_upper and ('SECTION' in doc_upper or 'PART' in doc_upper):
            return 'legislation'
    
    if 'NZLII' in source or 'NZLII' in source_collection:
        return 'case_law'
    
    if 'POLICE MANUAL' in source or 'POLICE' in source_collection:
        return 'police_manual'
    
    if 'CASE DOCUMENTS' in source_collection:
        return 'case_law'
    
    # Priority 2: Content-based detection
    # Legislation patterns
    if re.search(r'\b(CRIMES ACT|MISUSE OF DRUGS ACT|EVIDENCE ACT|BILL OF RIGHTS ACT)\s+\d{4}\b', doc_upper):
        return 'legislation'
    
    if re.search(r'(SECTION\s+\d+[A-Z]?|S\d+\([\d\w]+\)).*OF.*ACT', doc_upper):
        return 'legislation'
    
    # Case law patterns
    if re.search(r'\[\d{4}\]\s*\d+\s*(NZLR|NZSC|NZCA|NZHC|CRNZ)', doc_upper):
        return 'case_law'
    
    if re.search(r'\bR\s+V\s+[A-Z]', doc_upper):
        return 'case_law'
    
    if 'JUDGMENT' in doc_upper and 'COURT' in doc_upper:
        return 'case_law'
    
    if 'APPELLANT' in doc_upper or 'RESPONDENT' in doc_upper:
        return 'case_law'
    
    # Police manual patterns
    if re.search(r'POLICE\s+(MANUAL|POLICY|PROCEDURE)', doc_upper):
        return 'police_manual'
    
    if 'POLICE POWERS' in doc_upper or 'OFFICER MUST' in doc_upper:
        return 'police_manual'
    
    # Legal research patterns
    if any(x in doc_upper for x in ['ANALYSIS', 'RESEARCH NOTE', 'OVERVIEW', 'SUMMARY OF']):
        return 'legal_research'
    
    # Default to original category or unknown
    original = metadata.get('category', 'unknown')
    if original not in ['unknown', '']:
        return original
    
    return 'uncategorized'

def get_act_name(source, title, document):
    """Extract the Act name from legislation documents"""
    combined = f"{source} {title} {document[:500]}"
    
    # Common NZ Acts
    acts = [
        'Crimes Act 1961',
        'Misuse of Drugs Act 1975',
        'Evidence Act 2006',
        'Search and Surveillance Act 2012',
        'Criminal Procedure Act 2011',
        'Bill of Rights Act 1990',
        'Summary Offences Act 1981',
        'Oranga Tamariki Act 1989',
        "Victims' Rights Act 2002",
        'Sentencing Act 2002',
        'Parole Act 2002',
        'Bail Act 2000',
        'Policing Act 2008',
        'Immigration Act 2009',
        'Customs and Excise Act 2018',
        'Income Tax Act 2007',
        'Land Transfer Act 2017',
        'Property Law Act 2007',
        'Contract and Commercial Law Act 2017',
        'Companies Act 1993',
    ]
    
    combined_upper = combined.upper()
    for act in acts:
        if act.upper() in combined_upper:
            return act
    
    # Try to extract any Act name
    match = re.search(r'([A-Za-z\s\']+Act\s+\d{4})', combined)
    if match:
        return match.group(1)
    
    return None

def get_case_info(source, title, document):
    """Extract case citation info"""
    combined = f"{source} {title}"
    
    # Citation patterns
    citation_match = re.search(r'(\[\d{4}\]\s*\d+\s*(?:NZLR|NZSC|NZCA|NZHC|CRNZ)\s*\d+)', combined)
    if citation_match:
        return citation_match.group(1)
    
    # R v Name pattern
    rv_match = re.search(r'R\s+v\s+([A-Z][a-zA-Z\s]+)(?:\[|\(|\$)', combined)
    if rv_match:
        return f"R v {rv_match.group(1).strip()}"
    
    return None

def process_collection(client, source_name, target_collections, dry_run=True):
    """
    Process a source collection and distribute to target collections
    """
    print(f"\n{'='*70}")
    print(f"PROCESSING: {source_name}")
    print('='*70)
    
    try:
        source_coll = client.get_collection(source_name)
    except Exception as e:
        print(f"❌ Error accessing collection: {e}")
        return
    
    total = source_coll.count()
    if total == 0:
        print("Collection is empty")
        return
    
    print(f"Total documents: {total}")
    print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'LIVE (will modify)'}")
    
    # Statistics
    category_counts = defaultdict(int)
    act_counts = defaultdict(int)
    case_counts = defaultdict(int)
    
    # Get all documents in batches
    batch_size = 100
    offset = 0
    documents_to_move = defaultdict(list)  # target_coll -> [docs]
    
    print("\nAnalyzing documents...")
    while offset < total:
        results = source_coll.get(limit=batch_size, offset=offset)
        
        for doc_id, document, metadata in zip(
            results['ids'], results['documents'], results['metadatas']
        ):
            # Determine correct category
            category = determine_category(metadata, document)
            category_counts[category] += 1
            
            # Get additional metadata
            if category == 'legislation':
                act_name = get_act_name(
                    metadata.get('source', ''),
                    metadata.get('title', ''),
                    document
                )
                if act_name:
                    act_counts[act_name] += 1
            
            elif category == 'case_law':
                case_info = get_case_info(
                    metadata.get('source', ''),
                    metadata.get('title', ''),
                    document
                )
                if case_info:
                    case_counts[case_info] += 1
            
            # Determine target collection
            target_coll = target_collections.get(category, 'uncategorized')
            
            # Prepare for move
            new_metadata = {
                **metadata,
                'category': category,
                'recategorized_at': datetime.now().isoformat(),
                'original_collection': source_name,
            }
            
            # Only add non-None values
            if category == 'legislation' and act_name:
                new_metadata['act_name'] = act_name
            if category == 'case_law' and case_info:
                new_metadata['case_citation'] = case_info
            
            documents_to_move[target_coll].append({
                'id': doc_id,
                'document': document,
                'metadata': new_metadata
            })
        
        offset += batch_size
        if offset % 1000 == 0:
            print(f"  Processed {offset}/{total}...")
    
    # Print analysis results
    print(f"\n📊 Category Distribution:")
    for cat, cnt in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
        pct = (cnt / total) * 100
        target = target_collections.get(cat, 'uncategorized')
        print(f"  • {cat}: {cnt} ({pct:.1f}%) → {target}")
    
    if act_counts:
        print(f"\n📚 Top Acts Found:")
        for act, cnt in sorted(act_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  • {act}: {cnt}")
    
    if case_counts:
        print(f"\n⚖️  Top Cases Found:")
        for case, cnt in sorted(case_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  • {case}: {cnt}")
    
    # Execute moves
    if not dry_run:
        print(f"\n🚀 Executing moves...")
        for target_name, docs in documents_to_move.items():
            if not docs:
                continue
            
            # Get or create target collection
            try:
                target_coll = client.get_collection(target_name)
            except:
                target_coll = client.create_collection(
                    name=target_name,
                    metadata={'description': f'Auto-categorized {target_name}'}
                )
                print(f"  Created collection: {target_name}")
            
            # Add documents in batches
            batch_size = 100
            for i in range(0, len(docs), batch_size):
                batch = docs[i:i+batch_size]
                target_coll.add(
                    ids=[d['id'] for d in batch],
                    documents=[d['document'] for d in batch],
                    metadatas=[d['metadata'] for d in batch]
                )
            
            print(f"  Moved {len(docs)} documents to {target_name}")
        
        # Optionally delete from source (commented out for safety)
        # print(f"\n🗑️  Cleaning up source collection...")
        # client.delete_collection(source_name)
        # print(f"  Deleted source collection: {source_name}")
    else:
        print(f"\n💡 Dry run complete. No changes made.")
        print(f"   Would move:")
        for target_name, docs in documents_to_move.items():
            if docs:
                print(f"     • {len(docs)} docs → {target_name}")

def main():
    """Main re-categorization function"""
    print("=" * 70)
    print("NZ LEGAL RAG - SMART RE-CATEGORIZATION")
    print("=" * 70)
    print("\nThis script will:")
    print("  1. Analyze document content and sources")
    print("  2. Determine correct categories")
    print("  3. Distribute to appropriate collections")
    print("\n⚠️  Run in DRY RUN mode first to preview changes!")
    print("=" * 70)
    
    client = chromadb.PersistentClient(CHROMA_PATH)
    
    # Target collection mappings
    target_collections = {
        'legislation': 'nz_legislation',
        'case_law': 'nz_case_law',
        'police_manual': 'nz_police_manual',
        'legal_research': 'legal_research',
        'uncategorized': 'uncategorized_new',
    }
    
    # Process collections
    collections_to_process = [
        'uncategorized',
        'nz_legal_unified',
    ]
    
    for coll_name in collections_to_process:
        process_collection(client, coll_name, target_collections, dry_run=True)
    
    print("\n" + "=" * 70)
    print("DRY RUN COMPLETE")
    print("=" * 70)
    print("\nTo execute the changes, run with dry_run=False")
    print("Or modify this script to prompt for confirmation.")

if __name__ == "__main__":
    main()
