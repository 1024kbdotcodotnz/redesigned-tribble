import os
import sys
import json
import shutil
from pathlib import Path

PROJECT_ROOT = Path("/workspace/nz_legal_rag")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.file_parser import FileParser
from core.rag_engine import NZLegalRAG

UPLOAD_ROOT = Path("/workspace/uploads")
FOLDER_MAP = {
    "case_law": "nz_case_law",
    "nz_legislation": "nz_legislation",
    "police_manuals": "nz_police_manual",
}


def _doc_metadata(doc, folder_name: str, target_collection: str, zip_path: Path) -> dict:
    filename = getattr(doc, "filename", None) or "unknown"
    page = getattr(doc, "page_number", None)

    metadata = {
        "source": filename,
        "title": filename,
        "filename": filename,
        "upload_method": "workspace_cron_drop",
        "source_dir": folder_name,
        "archive_name": zip_path.name,
        "source_zip": str(zip_path.resolve()),
        "collection": target_collection,
    }

    if page is not None:
        metadata["page"] = page
        metadata["pagenumber"] = page

    return metadata


def main():
    parser = FileParser()
    rag = NZLegalRAG(
        db_path=os.getenv("CHROMA_DB_PATH", "/workspace/chroma_db_fresh"),
        embedding_model=os.getenv("EMBEDDING_MODEL", "nomic-embed-text"),
        llm_model=os.getenv("LLM_MODEL", "deepseek-r1:14b"),
        use_local_llm=False,
    )

    processed_root = UPLOAD_ROOT / "_processed"
    failed_root = UPLOAD_ROOT / "_failed"

    result = {
        "success": True,
        "files_processed": 0,
        "files_failed": 0,
        "total_chunks": 0,
        "details": [],
    }

    for folder_name, target_collection in FOLDER_MAP.items():
        source_dir = UPLOAD_ROOT / folder_name
        processed_dir = processed_root / folder_name
        failed_dir = failed_root / folder_name

        source_dir.mkdir(parents=True, exist_ok=True)
        processed_dir.mkdir(parents=True, exist_ok=True)
        failed_dir.mkdir(parents=True, exist_ok=True)

        for zip_path in sorted(source_dir.glob("*.zip")):
            try:
                zip_content = zip_path.read_bytes()
                parsed_docs, errors = parser.parse_zip(zip_content)

                if not parsed_docs:
                    result["files_failed"] += 1
                    result["details"].append({
                        "filename": zip_path.name,
                        "collection": target_collection,
                        "status": "failed",
                        "error": "No valid documents found in ZIP archive",
                    })
                    shutil.move(str(zip_path), str(failed_dir / zip_path.name))
                    continue

                documents = []
                for doc in parsed_docs:
                    name = str(getattr(doc, "filename", "unknown") or "unknown")

                    if name.endswith("_structure_manifest.json"):
                        continue

                    metadata = {
                        "filename": name,
                        "collection": str(target_collection),
                    }

                    page = getattr(doc, "page_number", None)
                    if page is not None:
                        try:
                            metadata["page"] = int(page)
                        except Exception:
                            metadata["page"] = str(page)

                    documents.append({
                        "name": name,
                        "content": doc.content,
                        "metadata": metadata,
                    })

                msg = rag.ingest_text(
                    documents=documents,
                    collection=target_collection,
                    metadata={
                        "upload_method": "workspace_cron_drop",
                        "source_dir": folder_name,
                        "archive_name": zip_path.name,
                        "source_zip": str(zip_path.resolve()),
                        "collection": target_collection,
                    },
                )

                chunks = 0
                try:
                    chunks = int(str(msg).split()[1])
                except Exception:
                    pass

                result["files_processed"] += len(parsed_docs)
                result["total_chunks"] += chunks

                for doc in parsed_docs:
                    result["details"].append({
                        "filename": doc.filename,
                        "archive_name": zip_path.name,
                        "collection": target_collection,
                        "status": "success",
                    })

                for error in errors:
                    result["details"].append({
                        **error,
                        "archive_name": zip_path.name,
                        "collection": target_collection,
                        "status": "failed",
                    })

                shutil.move(str(zip_path), str(processed_dir / zip_path.name))

            except Exception as e:
                result["success"] = False
                result["files_failed"] += 1
                result["details"].append({
                    "filename": zip_path.name,
                    "collection": target_collection,
                    "status": "failed",
                    "error": str(e),
                })
                try:
                    shutil.move(str(zip_path), str(failed_dir / zip_path.name))
                except Exception:
                    pass

    print(json.dumps(result))


if __name__ == "__main__":
    main()
