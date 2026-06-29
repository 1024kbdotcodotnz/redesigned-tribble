#!/bin/bash
# Quick deploy to RunPod - uploads only changed files
# Usage: ./deploy_to_runpod.sh <runpod-ssh-host>

set -e

RUNPOD_HOST="${1:-${RUNPOD_HOST}}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/id_ed25519}"

if [ -z "$RUNPOD_HOST" ]; then
    echo "Usage: ./deploy_to_runpod.sh <runpod-ssh-host>"
    echo "Or set RUNPOD_HOST environment variable"
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

echo "Deploying to RunPod: $RUNPOD_USER@$RUNPOD_IP"
echo ""

# Files to deploy
FILES=(
    "api/server.py"
    "core/file_parser.py"
    "web/streamlit_app.py"
    "web/upload_page.py"
    "requirements.txt"
)

echo "Deploying ${#FILES[@]} files..."

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  → $file"
        rsync -avz --progress \
            -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=no" \
            "$file" \
            "$RUNPOD_USER@$RUNPOD_IP:/workspace/nz_legal_rag/$file"
    else
        echo "  ✗ $file (not found)"
    fi
done

echo ""
echo "Installing dependencies on RunPod..."
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no \
    "$RUNPOD_USER@$RUNPOD_IP" \
    "cd /workspace/nz_legal_rag && pip install openpyxl python-docx beautifulsoup4 -q"

echo ""
echo "✓ Deploy complete!"
echo "Restart services on RunPod with: pkill -9 python; /workspace/start_legal_advisor.sh"
