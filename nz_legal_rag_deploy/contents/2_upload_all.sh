#!/bin/bash
# NZ Legal Advisor - Upload Everything to RunPod
# Run this on YOUR LOCAL MACHINE
# Usage: ./2_upload_all.sh <runpod-ssh-host>
#
# Examples:
#   ./2_upload_all.sh root@213.192.2.85
#   ./2_upload_all.sh 1ckakeoxjyi5pz-64411d4b@ssh.runpod.io

set -e

RUNPOD_HOST="$1"
RUNPOD_IP=""
RUNPOD_PORT="40033"  # Changed from 22 to your custom port
SSH_KEY="$HOME/.ssh/id_ed25519"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

if [ -z "$RUNPOD_HOST" ]; then
    echo -e "${RED}Usage: ./2_upload_all.sh <runpod-ssh-host>${NC}"
    echo ""
    echo "Examples:"
    echo "  ./2_upload_all.sh root@213.192.2.85"
    echo "  ./2_upload_all.sh 1ckakeoxjyi5pz-64411d4b@ssh.runpod.io"
    echo ""
    echo "Get this from RunPod Console → Connect → SSH Command"
    exit 1
fi

# Parse host
if echo "$RUNPOD_HOST" | grep -q "@"; then
    RUNPOD_USER=$(echo "$RUNPOD_HOST" | cut -d@ -f1)
    RUNPOD_IP=$(echo "$RUNPOD_HOST" | cut -d@ -f2)
else
    RUNPOD_USER="root"
    RUNPOD_IP="$RUNPOD_HOST"
fi

# Check for SSH key
if [ ! -f "$SSH_KEY" ]; then
    # Try runpod-specific key
    if [ -f "$HOME/.ssh/id_ed25519_runpod" ]; then
        SSH_KEY="$HOME/.ssh/id_ed25519_runpod"
        echo -e "${YELLOW}Using RunPod key: $SSH_KEY${NC}"
    else
        echo -e "${RED}❌ SSH key not found: $SSH_KEY${NC}"
        echo "Looking for alternative keys..."
        ls -la $HOME/.ssh/id_* 2>/dev/null || true
        exit 1
    fi
fi

echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  NZ Legal Advisor - Upload to RunPod${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
echo ""
echo "Target: $RUNPOD_USER@$RUNPOD_IP:$RUNPOD_PORT"
echo "SSH Key: $SSH_KEY"
echo "Source: $HOME/nz_legal_rag/"
echo "Destination: /workspace/nz_legal_rag/"
echo ""

# Test connection first
echo -e "${YELLOW}[1/5] Testing connection...${NC}"
if ! ssh -p $RUNPOD_PORT -o ConnectTimeout=10 -o StrictHostKeyChecking=no -i "$SSH_KEY" "$RUNPOD_USER@$RUNPOD_IP" "echo 'connected'" > /dev/null 2>&1; then
    echo -e "${RED}❌ Cannot connect to RunPod!${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Is the pod running? Check RunPod Console"
    echo "  2. Is the SSH key correct?"
    echo "  3. Try: ssh -p $RUNPOD_PORT -i $SSH_KEY $RUNPOD_USER@$RUNPOD_IP"
    exit 1
fi
echo -e "${GREEN}✓ Connected to RunPod${NC}"
echo ""

# Check if /workspace exists
echo -e "${YELLOW}[2/5] Checking /workspace...${NC}"
if ! ssh -p $RUNPOD_PORT -i "$SSH_KEY" "$RUNPOD_USER@$RUNPOD_IP" "[ -d /workspace ]" 2>/dev/null; then
    echo -e "${RED}❌ /workspace not found!${NC}"
    echo "Make sure Volume Disk is mounted."
    exit 1
fi
SPACE=$(ssh -p $RUNPOD_PORT -i "$SSH_KEY" "$RUNPOD_USER@$RUNPOD_IP" "df /workspace | tail -1 | awk '{print \$4}'" 2>/dev/null)
echo -e "${GREEN}✓ /workspace available (${SPACE}KB free)${NC}"
echo ""

# Check local files exist
echo -e "${YELLOW}[2.5/5] Checking local files...${NC}"
if [ ! -d "$HOME/nz_legal_rag" ]; then
    echo -e "${RED}❌ Local directory not found: $HOME/nz_legal_rag${NC}"
    exit 1
fi
if [ ! -f "$HOME/nz_legal_rag/web/streamlit_app.py" ]; then
    echo -e "${RED}❌ web/streamlit_app.py not found locally!${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Local files verified${NC}"
echo ""

# Create directory structure
echo -e "${YELLOW}[3/5] Creating directory structure...${NC}"
ssh -p $RUNPOD_PORT -i "$SSH_KEY" "$RUNPOD_USER@$RUNPOD_IP" "mkdir -p /workspace/nz_legal_rag/{chroma_db,tenant_data,logs,data,api,core,web,security,ingestion}" 2>/dev/null
echo -e "${GREEN}✓ Directories created${NC}"
echo ""

# Upload application code
echo -e "${YELLOW}[4/5] Uploading application code...${NC}"
echo "This includes: Python files, configs, scripts (excludes venv, cache)"
echo ""

cd "$HOME/nz_legal_rag"

rsync -avz --progress \
    -e "ssh -p $RUNPOD_PORT -i $SSH_KEY -o StrictHostKeyChecking=no" \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='*.log' \
    --exclude='backups' \
    --exclude='.git' \
    --exclude='*.tar.gz' \
    --exclude='id_ed25519*' \
    ./ \
    "$RUNPOD_USER@$RUNPOD_IP:/workspace/nz_legal_rag/"

echo ""
echo -e "${GREEN}✓ Code uploaded${NC}"
echo ""

# Upload database
echo -e "${YELLOW}[5/5] Uploading database...${NC}"
echo "This includes: chroma_db/, tenant_data/"
echo ""

if [ -d "chroma_db" ] && [ "$(ls -A chroma_db 2>/dev/null)" ]; then
    echo "Uploading chroma_db (~124MB)..."
    rsync -avz --progress \
        -e "ssh -p $RUNPOD_PORT -i $SSH_KEY -o StrictHostKeyChecking=no" \
        ./chroma_db/ \
        "$RUNPOD_USER@$RUNPOD_IP:/workspace/nz_legal_rag/chroma_db/"
    echo -e "${GREEN}✓ Database uploaded${NC}"
else
    echo -e "${YELLOW}⚠ chroma_db not found or empty - skipping${NC}"
fi

if [ -d "tenant_data" ] && [ "$(ls -A tenant_data 2>/dev/null)" ]; then
    echo "Uploading tenant_data (API keys)..."
    rsync -avz --progress \
        -e "ssh -p $RUNPOD_PORT -i $SSH_KEY -o StrictHostKeyChecking=no" \
        ./tenant_data/ \
        "$RUNPOD_USER@$RUNPOD_IP:/workspace/nz_legal_rag/tenant_data/"
    echo -e "${GREEN}✓ Tenant data uploaded${NC}"
else
    echo -e "${YELLOW}⚠ tenant_data not found - skipping${NC}"
fi

echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✓ Upload Complete!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
echo ""
echo "Files uploaded:"
ssh -p $RUNPOD_PORT -i "$SSH_KEY" "$RUNPOD_USER@$RUNPOD_IP" "ls -la /workspace/nz_legal_rag/web/ 2>/dev/null" 2>/dev/null || true
echo ""
echo "Next steps:"
echo "  1. SSH into RunPod:"
echo "     ssh -p $RUNPOD_PORT -i $SSH_KEY $RUNPOD_USER@$RUNPOD_IP"
echo ""
echo "  2. Start services:"
echo "     /workspace/start_legal_advisor.sh"
echo ""
echo "  3. Connect locally:"
echo "     ./3_connect.sh $RUNPOD_HOST"
echo ""

