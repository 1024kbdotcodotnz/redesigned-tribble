#!/bin/bash
# NZ Legal Advisor - Connect to RunPod with Port Forwarding
# Run this on YOUR LOCAL MACHINE
# Usage: ./3_connect.sh <runpod-ssh-host>

RUNPOD_HOST="$1"
SSH_KEY="$HOME/.ssh/id_ed25519"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

if [ -z "$RUNPOD_HOST" ]; then
    echo "Usage: ./3_connect.sh <runpod-ssh-host>"
    echo ""
    echo "Examples:"
    echo "  ./3_connect.sh 1ckakeoxjyi5pz-64411d4b@ssh.runpod.io"
    echo "  ./3_connect.sh root@213.192.2.106"
    echo ""
    echo "This will:"
    echo "  - SSH into RunPod"
    echo "  - Forward port 8501 (Web UI) → localhost:8501"
    echo "  - Forward port 8000 (API) → localhost:8000"
    echo ""
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
    if [ -f "$HOME/.ssh/id_ed25519_runpod" ]; then
        SSH_KEY="$HOME/.ssh/id_ed25519_runpod"
    else
        echo "❌ SSH key not found"
        exit 1
    fi
fi

echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  NZ Legal Advisor - Port Forwarding${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
echo ""
echo "Connecting to: $RUNPOD_USER@$RUNPOD_IP"
echo ""
echo -e "${YELLOW}Port forwarding:${NC}"
echo "  ${BLUE}http://localhost:8501${NC}  → Web Interface (Streamlit)"
echo "  ${BLUE}http://localhost:8000${NC}  → API Server (FastAPI)"
echo "  ${BLUE}http://localhost:8000/docs${NC} → API Documentation"
echo ""
echo -e "${YELLOW}Press Ctrl+C to disconnect${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
echo ""

# Test if services are running on RunPod first
echo "Checking if services are running on RunPod..."
if ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no -i "$SSH_KEY" "$RUNPOD_USER@$RUNPOD_IP" "curl -s http://localhost:8000/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ API server is running${NC}"
else
    echo -e "${YELLOW}⚠ API server not detected${NC}"
    echo "  You may need to start it:"
    echo "  ssh -i $SSH_KEY $RUNPOD_USER@$RUNPOD_IP"
    echo "  /workspace/start_legal_advisor.sh"
    echo ""
fi

# Connect with port forwarding
ssh -o ServerAliveInterval=60 \
    -o StrictHostKeyChecking=no \
    -L 8501:localhost:8501 \
    -L 8000:localhost:8000 \
    -i "$SSH_KEY" \
    "$RUNPOD_USER@$RUNPOD_IP"
