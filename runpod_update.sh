#!/bin/bash
# RunPod Update Script - Run this INSIDE RunPod container
# Updates the NZ Legal RAG deployment with new file upload features

set -e

cd /workspace/nz_legal_rag

echo "═══════════════════════════════════════════════════════════════"
echo "  NZ Legal RAG - RunPod Update"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Check if we're on RunPod
if [ ! -d "/workspace" ]; then
    echo "❌ Error: /workspace not found. Are you on RunPod?"
    exit 1
fi

echo "[1/4] Checking Python environment..."
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi
source .venv/bin/activate

echo "[2/4] Installing/updating dependencies..."
pip install -q openpyxl python-docx beautifulsoup4 PyPDF2

echo "[3/4] Verifying new modules..."
python3 -c "
from core.file_parser import FileParser
parser = FileParser()
print(f'✅ FileParser ready - {len(parser.SUPPORTED_TYPES)} file types supported')
for ext in ['.pdf', '.docx', '.xlsx', '.txt', '.html']:
    print(f'  • {ext}')
"

echo ""
echo "[4/4] Checking API endpoints..."
python3 -c "
from api.server import app
routes = [r.path for r in app.routes if hasattr(r, 'path')]
upload_routes = [r for r in routes if 'upload' in r]
print(f'✅ Upload endpoints registered:')
for r in upload_routes:
    print(f'  • {r}')
"

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  ✅ Update Complete!"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "New Features:"
echo "  • Multi-file upload (PDF, DOC, DOCX, TXT, XLSX, HTML, etc.)"
echo "  • ZIP archive upload (folder upload)"
echo "  • File type validation and preview"
echo ""
echo "Restart services:"
echo "  pkill -9 python; /workspace/start_legal_advisor.sh"
echo ""
