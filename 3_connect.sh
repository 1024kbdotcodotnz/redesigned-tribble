#!/bin/bash
# NZ Legal Advisor - Connect to RunPod with Port Forwarding
# Run this on YOUR LOCAL MACHINE
# Usage: ./3_connect.sh <runpod-ip>[:port]
#
# Examples:
#   ./3_connect.sh 69.30.85.79:22020
#   ./3_connect.sh root@69.30.85.79:22020
#   ./3_connect.sh 213.192.2.106

RUNPOD_ADDR="$1"
SSH_KEY="$HOME/.ssh/id_ed25519"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

if [ -z "$RUNPOD_ADDR" ]; then
    echo "Usage: ./3_connect.sh <runpod-ip>[:port]"
    echo ""
    echo "Examples:"
    echo "  ./3_connect.sh 69.30.85.79:22020"
    echo "  ./3_connect.sh root@69.30.85.79:22020"
    echo "  ./3_connect.sh 213.192.2.106"
    echo ""
    echo "This will:"
    echo "  - SSH into RunPod"
    echo "  - Forward port 5801 (Web UI)  → localhost:8501"
    echo "  - Forward port 8000 (API)     → localhost:8000"
    echo "  - Forward port 8080 (MCP)     → localhost:8080"
    echo ""
    exit 1
fi

# Parse user, IP and port
if echo "$RUNPOD_ADDR" | grep -q "@"; then
    RUNPOD_USER=$(echo "$RUNPOD_ADDR" | cut -d@ -f1)
    RUNPOD_IP=$(echo "$RUNPOD_ADDR" | cut -d@ -f2 | cut -d: -f1)
else
    RUNPOD_USER="root"
    RUNPOD_IP=$(echo "$RUNPOD_ADDR" | cut -d: -f1)
fi

RUNPOD_PORT=$(echo "$RUNPOD_ADDR" | grep -o ':[0-9]*$' | tr -d ':')
if [ -z "$RUNPOD_PORT" ]; then
    RUNPOD_PORT=22
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
echo "Connecting to: $RUNPOD_USER@$RUNPOD_IP (port $RUNPOD_PORT)"
echo ""
echo -e "${YELLOW}Port forwarding:${NC}"
echo "  ${BLUE}http://localhost:8501${NC}  → Web Interface (Streamlit)"
echo "  ${BLUE}http://localhost:8000${NC}  → API Server (FastAPI)"
echo "  ${BLUE}http://localhost:8000/docs${NC} → API Documentation"
echo "  ${BLUE}http://localhost:8080/mcp${NC} → MCP Server"
echo ""
echo -e "${YELLOW}Press Ctrl+C to disconnect${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
echo ""

# Test if services are running on RunPod first
echo "Checking if services are running on RunPod..."
if ssh -p "$RUNPOD_PORT" -o ConnectTimeout=5 -o StrictHostKeyChecking=no -i "$SSH_KEY" "$RUNPOD_USER@$RUNPOD_IP" "curl -s http://localhost:8000/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ API server is running${NC}"
else
    echo -e "${YELLOW}⚠ API server not detected${NC}"
    echo "  You may need to start it:"
    echo "  ssh -p $RUNPOD_PORT -i $SSH_KEY $RUNPOD_USER@$RUNPOD_IP"
    echo "  cd /workspace/nz_legal_rag && ./start_app.sh"
    echo ""
fi

# Connect with port forwarding
ssh -p "$RUNPOD_PORT" \
    -o ServerAliveInterval=60 \
    -o StrictHostKeyChecking=no \
    -L 8501:localhost:5801 \
    -L 8000:localhost:8000 \
    -L 8080:localhost:8080 \
    -i "$SSH_KEY" \
    "$RUNPOD_USER@$RUNPOD_IP"
