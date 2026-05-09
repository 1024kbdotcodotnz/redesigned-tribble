#!/bin/bash
# NZ Legal RAG - Clean Restart Script

APP_DIR="/workspace/nz_legal_rag"
cd "$APP_DIR"

echo "=== Killing stale processes ==="
pkill -f 'api.server' 2>/dev/null || true
pkill -f 'streamlit_app.py' 2>/dev/null || true
pkill -f 'mcp_server' 2>/dev/null || true
sleep 2

echo "=== Clearing Python cache ==="
find "$APP_DIR" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find "$APP_DIR" -name '*.pyc' -delete 2>/dev/null || true

echo "=== Checking Ollama ==="
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "ERROR: Ollama not running. Start it first: ollama serve"
    exit 1
fi
ollama list | grep -E "(llama3.1|deepseek-r1|nomic-embed-text)"

echo ""
echo "=== Starting API server ==="
PYTHONPATH="$APP_DIR" LLM_MODEL=deepseek-r1:14b python3 -m api.server > /tmp/api.log 2>&1 &
API_PID=$!

echo "=== Starting Streamlit ==="
streamlit run web/streamlit_app.py --server.port=8501 --server.address=0.0.0.0 --server.headless=true > /tmp/streamlit.log 2>&1 &
STREAM_PID=$!

echo "=== Waiting for health checks ==="
for i in {1..30}; do
    API_OK=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/health 2>/dev/null || echo "000")
    STREAM_OK=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8501/ 2>/dev/null || echo "000")
    if [ "$API_OK" = "200" ] && [ "$STREAM_OK" = "200" ]; then
        echo ""
        echo "=== ALL SERVICES READY ==="
        echo "API:       http://localhost:8000"
        echo "Streamlit: http://localhost:8501"
        echo "API PID:   $API_PID"
        echo "Web PID:   $STREAM_PID"
        exit 0
    fi
    echo -n "."
    sleep 1
done

echo ""
echo "WARNING: Services did not become healthy within 30s"
echo "API log:   tail -20 /tmp/api.log"
echo "Web log:   tail -20 /tmp/streamlit.log"
