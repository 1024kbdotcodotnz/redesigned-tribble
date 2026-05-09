#!/bin/bash
# NZ Legal RAG - Persistent Startup Script for RunPod
# Survives pod restarts by checking/reinstalling Ollama and running app in background

set -e

cd /workspace/nz_legal_rag 2>/dev/null || cd /workspace

LOG_DIR="/workspace/nz_legal_rag/logs"
mkdir -p "$LOG_DIR"
PIDFILE="/tmp/nzlegal_pids.txt"

# ============================================
# 1. CHECK/REINSTALL OLLAMA
# ============================================
install_ollama() {
    echo "→ Ollama not found. Installing..."
    curl -fsSL https://ollama.com/install.sh | sh
    echo "✓ Ollama installed"
}

if ! command -v ollama &> /dev/null; then
    install_ollama
fi

# Ensure Ollama binary is accessible
if ! command -v ollama &> /dev/null && [ -x "/usr/local/bin/ollama" ]; then
    export PATH="/usr/local/bin:$PATH"
fi

if ! command -v ollama &> /dev/null && [ -x "/usr/bin/ollama" ]; then
    export PATH="/usr/bin:$PATH"
fi

# Final check - try to reinstall if still missing
if ! command -v ollama &> /dev/null; then
    echo "⚠️  Ollama binary missing after check. Reinstalling..."
    install_ollama
fi

# ============================================
# 2. CONFIGURE OLLAMA ENVIRONMENT
# ============================================
export OLLAMA_MODELS=/workspace/ollama_models
export OLLAMA_HOST=0.0.0.0
export OLLAMA_GPU_LAYERS=999
export CUDA_VISIBLE_DEVICES=0
mkdir -p "$OLLAMA_MODELS"

# ============================================
# 3. START OLLAMA
# ============================================
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "→ Starting Ollama..."
    nohup ollama serve > "$LOG_DIR/ollama.log" 2>&1 &
    disown

    # Wait for Ollama to be ready
    for i in {1..30}; do
        if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
            echo "✓ Ollama is running"
            break
        fi
        sleep 1
    done
else
    echo "✓ Ollama already running"
fi

# ============================================
# 4. VERIFY/PULL MODELS
# ============================================
echo "→ Checking models..."

if ! ollama list | grep -q "deepseek-r1"; then
    echo "  → Pulling deepseek-r1:14b..."
    ollama pull deepseek-r1:14b
fi

if ! ollama list | grep -q "nomic-embed-text"; then
    echo "  → Pulling nomic-embed-text..."
    ollama pull nomic-embed-text:latest
fi

echo "✓ Models ready"

# ============================================
# 5. ACTIVATE PYTHON ENVIRONMENT
# ============================================
if [ -d "/workspace/nz_legal_rag/venv" ]; then
    source /workspace/nz_legal_rag/venv/bin/activate
elif [ -d "/workspace/nz_legal_rag/.venv" ]; then
    source /workspace/nz_legal_rag/.venv/bin/activate
fi

# ============================================
# 6. KILL STALE PROCESSES
# ============================================
for p in $(lsof -ti:8000 2>/dev/null || true); do kill -9 "$p" 2>/dev/null || true; done
for p in $(lsof -ti:8501 2>/dev/null || true); do kill -9 "$p" 2>/dev/null || true; done
sleep 1

# ============================================
# 7. START NZ LEGAL RAG SERVICES
# ============================================
echo "→ Starting API server..."
nohup python -m api.server > "$LOG_DIR/api.log" 2>&1 &
API_PID=$!
disown $API_PID

# Wait for API
for i in {1..90}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✓ API ready (PID: $API_PID)"
        break
    fi
    if ! kill -0 $API_PID 2>/dev/null; then
        echo "✗ API failed to start. Check logs/api.log"
        exit 1
    fi
    sleep 1
done

echo "→ Starting Web UI..."
nohup streamlit run web/streamlit_app.py --server.port 8501 --server.address 0.0.0.0 > "$LOG_DIR/web.log" 2>&1 &
WEB_PID=$!
disown $WEB_PID
sleep 3

if kill -0 $WEB_PID 2>/dev/null; then
    echo "✓ Web UI ready (PID: $WEB_PID)"
else
    echo "✗ Web UI failed to start. Check logs/web.log"
    exit 1
fi

# Save PIDs
echo "$API_PID $WEB_PID" > "$PIDFILE"

# ============================================
# 8. DONE
# ============================================
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  NZ Legal RAG is RUNNING"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "  🌐 Web UI:    http://localhost:8501"
echo "  🔌 API:       http://localhost:8000"
echo "  📚 API Docs:  http://localhost:8000/docs"
echo ""
echo "  PIDs: API=$API_PID, Web=$WEB_PID"
echo ""
echo "  You can disconnect SSH now."
echo "  To stop: run this script with 'stop' argument"
echo "═══════════════════════════════════════════════════════════════"
