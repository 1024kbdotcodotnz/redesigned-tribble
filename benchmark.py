#!/usr/bin/env python3
"""
NZ Legal RAG Performance Benchmark
Before/After comparison for optimization work.
"""

import os
import sys
import time
import tempfile
import shutil
import statistics
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent))

REPORTS = []

def bench(name: str, func, iterations: int = 1, warmup: int = 0):
    """Run a benchmark and collect stats."""
    print(f"\n▶ {name} ({iterations} run{'s' if iterations>1 else ''})")
    
    # Warmup
    for _ in range(warmup):
        func()
    
    times = []
    for i in range(iterations):
        t0 = time.perf_counter()
        result = func()
        t1 = time.perf_counter()
        elapsed = t1 - t0
        times.append(elapsed)
        print(f"  Run {i+1}: {elapsed:.3f}s")
    
    avg = statistics.mean(times)
    med = statistics.median(times)
    std = statistics.stdev(times) if len(times) > 1 else 0.0
    
    REPORTS.append({
        "name": name,
        "avg": avg,
        "median": med,
        "std": std,
        "min": min(times),
        "max": max(times),
        "iterations": iterations
    })
    return result


def print_report():
    print("\n" + "="*70)
    print("BENCHMARK REPORT")
    print("="*70)
    for r in REPORTS:
        print(f"\n{r['name']}")
        print(f"  Avg:   {r['avg']:.4f}s")
        print(f"  Median:{r['median']:.4f}s")
        print(f"  Min:   {r['min']:.4f}s")
        print(f"  Max:   {r['max']:.4f}s")
        if r['std']:
            print(f"  Stdev: {r['std']:.4f}s")
    print("="*70)


# =============================================================================
# 1. ChromaDB get_database_stats benchmark
# =============================================================================
def build_test_chroma(db_path: str, collection_name: str, num_chunks: int):
    """Create a temporary ChromaDB with N fake chunks."""
    import chromadb
    from chromadb.config import Settings
    
    if os.path.exists(db_path):
        shutil.rmtree(db_path)
    
    client = chromadb.PersistentClient(path=db_path)
    # Use a unique collection name per run to avoid collisions
    unique_name = f"{collection_name}_{num_chunks}_{int(time.time()*1000)}"
    coll = client.create_collection(name=unique_name)
    
    batch_size = 500
    for batch_start in range(0, num_chunks, batch_size):
        end = min(batch_start + batch_size, num_chunks)
        ids = [f"chunk_{i}" for i in range(batch_start, end)]
        docs = [f"This is legal text chunk number {i} with some statutory references and case law citations embedded within it for realistic sizing." * 10 for i in range(batch_start, end)]
        metas = [{"source": f"act_{i % 100}.pdf", "chunk_index": i} for i in range(batch_start, end)]
        coll.add(ids=ids, documents=docs, metadatas=metas)
    
    return client, coll


def benchmark_stats():
    db_path = "/tmp/bench_chroma_stats"
    
    # --- 5k chunks ---
    client, coll = build_test_chroma(db_path, "nz_legislation", 5000)
    
    def old_stats():
        chunk_count = coll.count()
        unique_docs = 0
        if chunk_count > 0:
            res = coll.get(include=["metadatas"])
            sources = set()
            for m in res["metadatas"]:
                src = m.get("source") or m.get("title") or m.get("filename") or m.get("act_name") or "unknown"
                sources.add(src)
            unique_docs = len(sources)
        return {"count": chunk_count, "documents": unique_docs}
    
    def new_stats():
        chunk_count = coll.count()
        return {"count": chunk_count, "documents": chunk_count}
    
    bench("Stats OLD (get() + set dedup) 5k chunks", old_stats, iterations=5, warmup=1)
    bench("Stats NEW (count() only) 5k chunks", new_stats, iterations=5, warmup=1)
    shutil.rmtree(db_path)
    
    # --- 20k chunks ---
    print("\n  Scaling to 20k chunks...")
    client, coll = build_test_chroma(db_path, "nz_legislation", 20000)
    bench("Stats OLD (get() + set dedup) 20k chunks", old_stats, iterations=3, warmup=1)
    bench("Stats NEW (count() only) 20k chunks", new_stats, iterations=3, warmup=1)
    shutil.rmtree(db_path)


# =============================================================================
# 2. PDF Parsing benchmark
# =============================================================================
PDF_FILES = [
    "~/Documents/Crimes Act 1961.pdf",
    "~/Documents/Privacy Act 2020.pdf",
    "~/Documents/New Zealand Bill of Rights Act 1990.pdf",
    "~/Documents/Corrections Act 2004.pdf",
]


def benchmark_pdf_parsing():
    files = [os.path.expanduser(p) for p in PDF_FILES if os.path.exists(os.path.expanduser(p))]
    if not files:
        print("  Skipping PDF benchmark — no PDFs found")
        return
    
    contents = [Path(f).read_bytes() for f in files]
    
    # --- PyPDF2 ---
    def parse_pypdf2():
        import PyPDF2
        total = 0
        for content in contents:
            reader = PyPDF2.PdfReader(content)
            text = ""
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    text += t
            total += len(text)
        return total
    
    # --- PyMuPDF ---
    def parse_pymupdf():
        import fitz
        total = 0
        for content in contents:
            doc = fitz.open(stream=content, filetype="pdf")
            text = ""
            for page in doc:
                text += page.get_text()
            total += len(text)
        return total
    
    bench("PDF PyPDF2 (4 files)", parse_pypdf2, iterations=5, warmup=1)
    bench("PDF PyMuPDF (4 files)", parse_pymupdf, iterations=5, warmup=1)


# =============================================================================
# 3. File parsing throughput (sequential vs parallel)
# =============================================================================
def benchmark_file_parsing():
    from core.file_parser import FileParser
    
    files = [os.path.expanduser(p) for p in PDF_FILES if os.path.exists(os.path.expanduser(p))]
    if not files:
        print("  Skipping file parsing benchmark")
        return
    
    contents = [(Path(f).read_bytes(), os.path.basename(f)) for f in files]
    parser = FileParser()
    
    def sequential():
        results, errors = parser.parse_multiple(contents)
        return len(results)
    
    def parallel():
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(parser.parse_file, c, n) for c, n in contents]
            results = []
            for f in futures:
                try:
                    results.append(f.result())
                except Exception:
                    pass
        return len(results)
    
    bench("File parse SEQUENTIAL (4 PDFs)", sequential, iterations=5, warmup=1)
    bench("File parse PARALLEL (4 PDFs)", parallel, iterations=5, warmup=1)


# =============================================================================
# 4. Embedding cache benchmark (synthetic)
# =============================================================================
def benchmark_embedding_cache():
    # Simulate an embedding function that takes 50ms
    def slow_embed(query: str):
        time.sleep(0.05)
        return [0.1] * 768
    
    queries = ["search warrant requirements nz", "section 21 NZBORA", "disclosure obligations CPA 2011"] * 10
    
    def uncached():
        return [slow_embed(q) for q in queries]
    
    @lru_cache(maxsize=512)
    def cached_embed(query: str):
        return slow_embed(query)
    
    def cached():
        return [cached_embed(q) for q in queries]
    
    bench("Embedding NO CACHE (30 queries, 3 unique)", uncached, iterations=3, warmup=0)
    bench("Embedding WITH LRU CACHE (30 queries, 3 unique)", cached, iterations=3, warmup=0)


if __name__ == "__main__":
    import json
    
    print("="*70)
    print("NZ LEGAL RAG — PERFORMANCE BENCHMARK")
    print("="*70)
    
    benchmark_stats()
    benchmark_pdf_parsing()
    benchmark_file_parsing()
    benchmark_embedding_cache()
    
    print_report()
    
    # Save report
    report_file = sys.argv[1] if len(sys.argv) > 1 else "benchmark_report.json"
    with open(report_file, "w") as f:
        json.dump(REPORTS, f, indent=2)
    print(f"\nReport saved to {report_file}")
