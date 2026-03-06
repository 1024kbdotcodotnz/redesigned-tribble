#!/bin/bash
# Connect to RunPod with port forwarding
# Usage: ./connect_runpod.sh <your-runpod-ip>[:port]

RUNPOD_ADDR="$1"

if [ -z "$RUNPOD_ADDR" ]; then
    echo "Usage: ./connect_runpod.sh <your-runpod-ip>[:port]"
    echo "Examples:"
    echo "  ./connect_runpod.sh 194.36.144.12"
    echo "  ./connect_runpod.sh 213.192.2.88:40141"
    echo ""
    echo "This will:"
    echo "  - SSH into your RunPod instance"
    echo "  - Forward port 8501 (Web UI) to localhost:8501"
    echo "  - Forward port 8000 (API) to localhost:8000"
    echo ""
    echo "Then access:"
    echo "  Web UI: http://localhost:8501"
    echo "  API:    http://localhost:8000"
    exit 1
fi

# Parse IP and port
RUNPOD_IP=$(echo "$RUNPOD_ADDR" | cut -d: -f1)
RUNPOD_PORT=$(echo "$RUNPOD_ADDR" | grep -o ':[0-9]*$' | tr -d ':')

# Default to port 22 if not specified
if [ -z "$RUNPOD_PORT" ]; then
    RUNPOD_PORT=22
fi

echo "Connecting to RunPod at $RUNPOD_IP (port $RUNPOD_PORT)..."
echo ""
echo "══════════════════════════════════════════════════"
echo "  Port Forwarding Active"
echo "══════════════════════════════════════════════════"
echo ""
echo "  Local → Remote"
echo "  ──────────────────────"
echo "  http://localhost:8501 → Web Interface"
echo "  http://localhost:8000 → API Server"
echo "  http://localhost:8000/docs → API Docs"
echo ""
echo "  Press Ctrl+C to disconnect"
echo "══════════════════════════════════════════════════"
echo ""

ssh -p $RUNPOD_PORT -L 8501:localhost:8501 -L 8000:localhost:8000 root@$RUNPOD_IP
