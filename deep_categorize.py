#!/usr/bin/env python3
"""
Deep Database Categorization Script
Analyzes and re-categorizes the large collections based on content analysis
"""

import chromadb
import re
from collections import defaultdict
from pathlib import Path

CHROMA_PATH = "./chroma_db"

def analyze_collection_content(collection, name, sample_limit=1000):
    """Deep analysis of collection content to determine actual categories"""
    print(f"\n{'='*70}")
    print(f"ANALYZING: {name} ({collection.count()} documents)")
    print('='*70)
    
    count = collection.count()
    if count == 0:
        return {}
    
    # Get all documents (or large sample)
    sample_size = min(sample_limit, count)
    results = collection.get(limit=sample_size)
    
    # Analyze metadata patterns
    categories = defaultdict(int)
    sources = defaultdict(int)
    titles = defaultdict(int)
    source_collections = defaultdict(int)
    
    # Content-based patterns
    content_indicators = {
        'legislation': 0,
        'case_law': 0,
        'police_manual': 0,
        'legal_research': 0,
        'unknown': 0
    }
    
    for i, (doc_id, document, metadata) in enumerate(zip(
        results['ids'], results['documents'], results['metadatas']
    )):
        # Metadata analysis
        cat = metadata.get('category', 'unknown')
        categories[cat] += 1
        
        src = metadata.get('source', '')
        sources[src[:80]] += 1
        
        title = metadata.get('title', '')
        if title:
            titles[title[:60]] += 1
        
        src_coll = metadata.get('source_collection', '')
        if src_coll:
            source_collections[src_coll] += 1
        
        # Content-based detection
        doc_upper = document[:1000].upper()
        
        # Legislation indicators
        if any(x in doc_upper for x in ['ACT ', 'SECTION ', 'REGULATION', 'STATUTE', 'PARLIAMENT']):
            if re.search(r'\b(ACT|BILL)\s+\d{4}\b', doc_upper):
                content_indicators['legislation'] += 1
            elif 'SECTION' in doc_upper and ('ACT' in doc_upper or 'LAW' in doc_upper):
                content_indicators['legislation'] += 1
        
        # Case law indicators
        if any(x in doc_upper for x in ['V ', 'VS ', 'VERSUS', 'APPELLANT', 'RESPONDENT', 'JUDGMENT', 'COURT OF']):
            if re.search(r'\[\d{4}\]\s*\d+\s*(NZLR|NZSC|NZCA|NZHC)', doc_upper):
                content_indicators['case_law'] += 1
            elif 'R V ' in doc_upper or 'R VS ' in doc_upper:
                content_indicators['case_law'] += 1
        
        # Police manual indicators
        if any(x in doc_upper for x in ['POLICE MANUAL', 'POLICY', 'PROCEDURE', 'OFFICER MUST', 'POLICE POWERS']):
            content_indicators['police_manual'] += 1
        
        # Legal research indicators
        if any(x in doc_upper for x in ['ANALYSIS', 'RESEARCH', 'OVERVIEW', 'SUMMARY', 'GUIDE TO']):
            content_indicators['legal_research'] += 1
    
    # Print results
    print(f"\n📊 Metadata Categories (from {sample_size} samples):")
    for cat, cnt in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        pct = (cnt / sample_size) * 100
        print(f"  • {cat}: {cnt} ({pct:.1f}%)")
    
    print(f"\n📚 Source Collections:")
    for src, cnt in sorted(source_collections.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  • {src}: {cnt}")
    
    print(f"\n🔍 Content-Based Detection:")
    for ind, cnt in sorted(content_indicators.items(), key=lambda x: x[1], reverse=True):
        if cnt > 0:
            pct = (cnt / sample_size) * 100
            print(f"  • {ind}: {cnt} ({pct:.1f}%)")
    
    print(f"\n📝 Common Source Patterns:")
    for src, cnt in sorted(sources.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  • {src[:60]}...: {cnt}")
    
    return {
        'total': count,
        'categories': dict(categories),
        'content_indicators': content_indicators,
        'source_collections': dict(source_collections)
    }

def suggest_categorization(collection_name, analysis):
    """Suggest how to re-categorize based on analysis"""
    print(f"\n💡 CATEGORIZATION RECOMMENDATIONS:")
    print('-' * 50)
    
    categories = analysis.get('categories', {})
    content = analysis.get('content_indicators', {})
    total = analysis.get('total', 0)
    
    # Determine primary category
    primary_meta = max(categories.items(), key=lambda x: x[1]) if categories else ('unknown', 0)
    primary_content = max(content.items(), key=lambda x: x[1]) if content else ('unknown', 0)
    
    print(f"  Current metadata says: {primary_meta[0]} ({primary_meta[1]} docs)")
    print(f"  Content analysis suggests: {primary_content[0]} ({primary_content[1]} docs)")
    
    # Specific recommendations
    if collection_name == 'uncategorized':
        print(f"\n  ⚠️  PRIORITY: Re-categorize these {total} documents!")
        print("  Suggested target collections:")
        
        if content.get('legislation', 0) > 100:
            print("    → Move legislation docs to nz_legislation")
        if content.get('case_law', 0) > 100:
            print("    → Move case law docs to nz_case_law")
        if content.get('police_manual', 0) > 100:
            print("    → Move police docs to nz_police_manual")
        if content.get('legal_research', 0) > 100:
            print("    → Keep as legal_research or nz_legal_research")
    
    elif collection_name == 'nz_legal_unified':
        print(f"\n  📝 ANALYSIS: This collection has {total} docs")
        if primary_meta[0] == 'legislation' and primary_content[0] == 'legislation':
            print("  ✅ Consistent: All documents are legislation")
            print("  💡 Recommendation: Split by Act name (Crimes Act, Misuse of Drugs Act, etc.)")
        else:
            print("  ⚠️  MIXED: Documents have different content types")
            print("  💡 Recommendation: Re-distribute to appropriate collections")
    
    elif collection_name in ['user_uploads', 'user_documents']:
        print(f"\n  👤 USER CONTENT: {total} documents")
        print("  💡 Recommendation: Merge these collections (appears to be duplicate)")
    
    return {
        'primary_metadata_category': primary_meta[0],
        'primary_content_category': primary_content[0],
        'recommendation': 'analyze' if primary_meta[0] != primary_content[0] else 'keep'
    }

def deep_categorize():
    """Main deep categorization function"""
    print("=" * 70)
    print("NZ LEGAL RAG - DEEP DATABASE CATEGORIZATION")
    print("=" * 70)
    print("\nThis script performs deep content analysis to properly")
    print("categorize the large collections based on actual document content.")
    
    client = chromadb.PersistentClient(CHROMA_PATH)
    
    # Collections to analyze
    collections_to_analyze = [
        'uncategorized',
        'nz_legal_unified', 
        'user_uploads',
        'user_documents'
    ]
    
    all_analysis = {}
    
    for coll_name in collections_to_analyze:
        try:
            coll = client.get_collection(coll_name)
            analysis = analyze_collection_content(coll, coll_name)
            all_analysis[coll_name] = analysis
            
            if analysis:
                suggest_categorization(coll_name, analysis)
        except Exception as e:
            print(f"\n❌ Error analyzing {coll_name}: {e}")
    
    # Summary
    print("\n" + "=" * 70)
    print("EXECUTIVE SUMMARY")
    print("=" * 70)
    
    total_uncategorized = all_analysis.get('uncategorized', {}).get('total', 0)
    total_unified = all_analysis.get('nz_legal_unified', {}).get('total', 0)
    total_user = all_analysis.get('user_uploads', {}).get('total', 0)
    
    print(f"\n📊 Total Documents Needing Review:")
    print(f"  • uncategorized: {total_uncategorized:,}")
    print(f"  • nz_legal_unified: {total_unified:,}")
    print(f"  • user_uploads/documents: {total_user:,}")
    print(f"  • TOTAL: {total_uncategorized + total_unified + total_user:,}")
    
    print("\n🎯 Recommended Actions:")
    print("  1. Re-categorize 'uncategorized' collection by content analysis")
    print("  2. Verify 'nz_legal_unified' is truly all legislation")
    print("  3. Merge 'user_uploads' and 'user_documents' (duplicates)")
    print("  4. Create new collections for distinct categories")

if __name__ == "__main__":
    deep_categorize()
