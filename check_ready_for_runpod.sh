#!/bin/bash
# Pre-flight check before uploading to RunPod

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "════════════════════════════════════════════════════════════════"
echo "  NZ Legal RAG - RunPod Upload Readiness Check"
echo "════════════════════════════════════════════════════════════════"
echo ""

cd "$HOME/nz_legal_rag"

ERRORS=0
WARNINGS=0

# Check 1: Required files exist
echo -e "${YELLOW}[Check 1/10] Required files...${NC}"
for file in docker-compose.yml Dockerfile.api Dockerfile.web requirements.txt api/server.py web/streamlit_app.py core/rag_engine.py; do
    if [ -f "$file" ]; then
        echo "  ✓ $file"
    else
        echo "  ✗ $file MISSING"
        ((ERRORS++))
    fi
done
echo ""

# Check 2: Directories exist
echo -e "${YELLOW}[Check 2/10] Required directories...${NC}"
for dir in api core web security ingestion config data tenant_data; do
    if [ -d "$dir" ]; then
        echo "  ✓ $dir/"
    else
        echo "  ✗ $dir/ MISSING"
        ((ERRORS++))
    fi
done
echo ""

# Check 3: chroma_db check
echo -e "${YELLOW}[Check 3/10] ChromaDB database...${NC}"
if [ -L "chroma_db" ]; then
    echo "  ℹ chroma_db is a symlink"
    if [ -d "chroma_db" ]; then
        SIZE=$(du -sh chroma_db 2>/dev/null | cut -f1)
        COUNT=$(find chroma_db -type f 2>/dev/null | wc -l)
        echo "  ✓ Symlink target exists ($SIZE, $COUNT files)"
    else
        echo "  ✗ Symlink target NOT FOUND"
        ((ERRORS++))
    fi
elif [ -d "chroma_db" ]; then
    SIZE=$(du -sh chroma_db 2>/dev/null | cut -f1)
    echo "  ✓ chroma_db directory exists ($SIZE)"
else
    echo "  ✗ chroma_db NOT FOUND"
    ((ERRORS++))
fi
echo ""

# Check 4: tenant_data check
echo -e "${YELLOW}[Check 4/10] Tenant data...${NC}"
if [ -d "tenant_data" ] && [ -f "tenant_data/tenants.json" ]; then
    echo "  ✓ tenant_data/tenants.json exists"
else
    echo "  ⚠ tenant_data/tenants.json not found (will be created on first run)"
    ((WARNINGS++))
fi
echo ""

# Check 5: Security - .env should exist locally but not be uploaded
echo -e "${YELLOW}[Check 5/10] Environment files...${NC}"
if [ -f ".env" ]; then
    echo "  ✓ .env exists locally (will be excluded from upload)"
else
    echo "  ⚠ .env not found locally (create from .env.example)"
    ((WARNINGS++))
fi
if [ -f ".env.example" ]; then
    echo "  ✓ .env.example exists"
else
    echo "  ⚠ .env.example not found"
    ((WARNINGS++))
fi
echo ""

# Check 6: SSH key check
echo -e "${YELLOW}[Check 6/10] SSH configuration...${NC}"
SSH_KEY="$HOME/.ssh/id_ed25519"
if [ -f "$SSH_KEY" ]; then
    echo "  ✓ SSH key exists: $SSH_KEY"
else
    echo "  ⚠ SSH key not found: $SSH_KEY"
    echo "    Will look for alternative keys during upload"
    ((WARNINGS++))
fi
echo ""

# Check 7: Upload script check
echo -e "${YELLOW}[Check 7/10] Upload script...${NC}"
if [ -f "2_upload_all.sh" ]; then
    if grep -q "rsync.*-L" "2_upload_all.sh"; then
        echo "  ✓ 2_upload_all.sh has symlink resolution (-L flag)"
    else
        echo "  ⚠ 2_upload_all.sh may not handle symlinks properly"
        ((WARNINGS++))
    fi
    if grep -q "\.env" "2_upload_all.sh" | grep -q "exclude"; then
        echo "  ✓ 2_upload_all.sh excludes .env file"
    fi
else
    echo "  ✗ 2_upload_all.sh NOT FOUND"
    ((ERRORS++))
fi
echo ""

# Check 8: File sizes
echo -e "${YELLOW}[Check 8/10] File sizes...${NC}"
CODE_SIZE=$(du -sh . --exclude=chroma_db --exclude=venv --exclude=.venv --exclude=.git 2>/dev/null | cut -f1)
echo "  ℹ Code size (excl. chroma_db, venv): $CODE_SIZE"
if [ -d "chroma_db" ]; then
    DB_SIZE=$(du -sh chroma_db 2>/dev/null | cut -f1)
    echo "  ℹ ChromaDB size: $DB_SIZE"
fi
echo ""

# Check 9: Data directories
echo -e "${YELLOW}[Check 9/10] Data directories...${NC}"
for dir in data/legislation data/case_law data/police_manual; do
    if [ -d "$dir" ]; then
        COUNT=$(find "$dir" -type f 2>/dev/null | wc -l)
        echo "  ✓ $dir ($COUNT files)"
    else
        echo "  ⚠ $dir not found"
        ((WARNINGS++))
    fi
done
echo ""

# Check 10: Clean unnecessary files
echo -e "${YELLOW}[Check 10/10] Clean build artifacts...${NC}"
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.swp" -delete 2>/dev/null || true
find . -name ".DS_Store" -delete 2>/dev/null || true
echo "  ✓ Cleaned Python cache and temp files"
echo ""

# Summary
echo "════════════════════════════════════════════════════════════════"
if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}  ✓ ALL CHECKS PASSED - Ready for upload!${NC}"
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}  ⚠ READY WITH WARNINGS ($WARNINGS warnings)${NC}"
    echo "  You can proceed with upload, but review warnings above."
else
    echo -e "${RED}  ✗ ERRORS FOUND ($ERRORS errors, $WARNINGS warnings)${NC}"
    echo "  Please fix errors before uploading."
fi
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Upload command:"
echo "  ./2_upload_all.sh root@<runpod-ip>:<port>"
echo ""
echo "Or with SSH key:"
echo "  ./2_upload_all.sh <user>@<host>"
echo ""

exit $ERRORS
