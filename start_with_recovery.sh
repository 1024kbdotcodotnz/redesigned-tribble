#!/bin/bash
# NZ Legal RAG - Start with Auto-Recovery
# This script ensures Ollama is ready before starting the API and Streamlit

set -e

cd /workspace/nz_legal_rag

echo "═══════════════════════════════════════════════════════════════"
echo "  NZ Legal RAG - Starting with Auto-Recovery"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Step 1: Run Ollama auto-recovery
if [ -f "./ollama_auto_setup.sh" ]; then
    chmod +x ./ollama_auto_setup.sh
    ./ollama_auto_setup.sh
else
    echo "⚠ ollama_auto_setup.sh not found, skipping auto-recovery"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  Starting Application Services"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Step 2: Kill any existing Python processes
echo "Cleaning up existing processes..."
pkill -9 -f "python.*api.server" 2>/dev/null || true
pkill -9 -f "streamlit" 2>/dev/null || true
sleep 2
echo "✓ Cleanup complete"
echo ""

# Step 3: Start API server
echo "Starting API server on port 8000..."
source .venv/bin/activate
export EMBEDDING_MODEL=all-minilm:latest
export OLLAMA_HOST=http://localhost:11434
export CHROMA_DB_PATH=./chroma_db
export ADMIN_API_KEY=eeb7ddacf4f3d4ed69aca0551f14d37f20d27a2c84d0a649ecc2be78ce09ece1

nohup python3 -m api.server > logs/api.log 2>&1 &
API_PID=$!
echo "✓ API server started (PID: $API_PID)"

# Wait for API to be ready
echo "Waiting for API to be ready..."
for i in $(seq 1 30); do
    if curl -s localhost:8000/health > /dev/null 2>&1; then
        echo "✓ API is ready"
        break
    fi
    sleep 1
    echo -n "."
done
echo ""

# Step 4: Start Streamlit
echo "Starting Streamlit on port 5801..."
nohup streamlit run web/streamlit_app.py \
    --server.port=5801 \
    --server.address=0.0.0.0 \
    --server.headless=true \
    > logs/streamlit.log 2>&1 &
STREAMLIT_PID=$!
echo "✓ Streamlit started (PID: $STREAMLIT_PID)"

# Wait for Streamlit
echo "Waiting for Streamlit to be ready..."
for i in $(seq 1 30); do
    if curl -s localhost:5801 > /dev/null 2>&1; then
        echo "✓ Streamlit is ready"
        break
    fi
    sleep 1
    echo -n "."
done
echo ""

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  ✓ All Services Started Successfully!"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "Access URLs:"
echo "  • API:      http://$(hostname -I | awk '{print $1}'):8000"
echo "  • Streamlit: http://$(hostname -I | awk '{print $1}'):5801"
echo "  • API Docs:  http://$(hostname -I | awk '{print $1}'):8000/docs"
echo ""
echo "Process IDs:"
echo "  • API:       $API_PID"
echo "  • Streamlit: $STREAMLIT_PID"
echo ""
echo "Logs:"
echo "  • API:       tail -f logs/api.log"
echo "  • Streamlit: tail -f logs/streamlit.log"
echo ""
echo "To stop: pkill -9 -f 'api.server|streamlit'"
echo ""

# Keep script running if called directly
if [ "${KEEP_ALIVE:-false}" = "true" ]; then
    echo "Keeping script alive (press Ctrl+C to stop)..."
    wait
fi
