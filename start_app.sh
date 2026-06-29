#!/bin/bash
# NZ Legal RAG Demo Startup Script

export OLLAMA_CONTEXT_LENGTH=${OLLAMA_CONTEXT_LENGTH:-24576}
# This script starts the API server and the Streamlit web UI.

set -e

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$APP_DIR"

# Load environment safely
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

# Use the .venv Python environment explicitly
PYTHON_BIN="$APP_DIR/.venv/bin/python"
STREAMLIT_BIN="$APP_DIR/.venv/bin/streamlit"
if [ ! -f "$PYTHON_BIN" ]; then
    echo "❌ .venv not found. Please create a virtual environment first."
    exit 1
fi

# Check Ollama
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "⚠️  Ollama not running. Starting ollama serve..."
    ollama serve &
    sleep 3
fi

echo "✓ Ollama is running"
ollama list | grep -E "(nomic-embed-text|deepseek-v3)" || true

# Prevent Streamlit first-run email prompt
mkdir -p ~/.streamlit
if [ ! -f ~/.streamlit/credentials.toml ]; then
    echo '[general]' > ~/.streamlit/credentials.toml
    echo 'email = ""' >> ~/.streamlit/credentials.toml
fi
export STREAMLIT_BROWSER_GATHERUSAGESTATS=false

# Verify chroma_db symlink is valid
if [ ! -d "/workspace/chroma_db_fresh" ]; then
    echo "❌ chroma_db directory missing or broken symlink. Please fix before starting."
    exit 1
fi
echo "✓ chroma_db is accessible"

# Start API server
echo ""
echo "🚀 Starting API server on port ${API_PORT:-8000}..."
$PYTHON_BIN -m api.server &
API_PID=$!

# Wait for API to be ready
echo "⏳ Waiting for API to start..."
for i in {1..30}; do
    if curl -s http://localhost:${API_PORT:-8000}/health > /dev/null 2>&1; then
        echo "✓ API server ready"
        break
    fi
    sleep 1
done

# Start MCP server (optional – set MCP_ENABLED=1 to enable)
MCP_PID=""
if [ "${MCP_ENABLED:-0}" = "1" ]; then
    echo ""
    echo "🔌 Starting MCP server on port ${MCP_PORT:-8080}..."
    $PYTHON_BIN -m api.mcp_server \
        --transport "${MCP_TRANSPORT:-streamable-http}" \
        --host "${MCP_HOST:-0.0.0.0}" \
        --port "${MCP_PORT:-8080}" \
        --path "${MCP_PATH:-/mcp}" &
    MCP_PID=$!
    echo "✓ MCP server started"
fi

# Start web interface on port 5801 (exposed demo port)
echo ""
echo "🌐 Starting web interface on port 5801..."
$STREAMLIT_BIN run web/streamlit_app.py --server.port 5801 --server.address 0.0.0.0 &
WEB_PID=$!

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  NZ Legal RAG Demo is running!"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "  🌐 Web Interface:  http://localhost:5801"
echo "  🔌 API:            http://localhost:${API_PORT:-8000}"
echo "  📚 API Docs:       http://localhost:${API_PORT:-8000}/docs"
if [ -n "$MCP_PID" ]; then
    echo "  🔗 MCP:            http://localhost:${MCP_PORT:-8080}${MCP_PATH:-/mcp}"
fi
echo ""
echo "  Demo Accounts:"
echo "    admin / demo-admin-2024!"
echo "    staff / demo-staff-2024!"
echo "    user  / demo-user-2024!"
echo ""
echo "  Press Ctrl+C to stop"
echo ""
echo "═══════════════════════════════════════════════════════════════"

# Wait for interrupt
trap "echo ''; echo 'Shutting down...'; kill $API_PID $WEB_PID $MCP_PID 2>/dev/null; exit" INT
wait
