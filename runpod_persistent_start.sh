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
export OLLAMA_HOST=127.0.0.1
export OLLAMA_GPU_LAYERS=999
export OLLAMA_NUM_PARALLEL=1
export OLLAMA_MAX_LOADED_MODELS=1
export OLLAMA_KEEP_ALIVE=-1
export OLLAMA_FLASH_ATTENTION=1
export OLLAMA_KV_CACHE_TYPE=q4_0
export OLLAMA_CONTEXT_LENGTH=16384
export OLLAMA_LOAD_TIMEOUT=10m
export CUDA_VISIBLE_DEVICES=0
unset OLLAMA_VULKAN 2>/dev/null || true
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

LLM_MODEL="${LLM_MODEL:-qwen2.5:14b}"
EMBEDDING_MODEL="${EMBEDDING_MODEL:-nomic-embed-text:latest}"

if ! ollama list | grep -q "$LLM_MODEL"; then
    echo "  → Pulling $LLM_MODEL..."
    ollama pull "$LLM_MODEL"
fi

if ! ollama list | grep -q "$EMBEDDING_MODEL"; then
    echo "  → Pulling $EMBEDDING_MODEL..."
    ollama pull "$EMBEDDING_MODEL"
fi

echo "✓ Models ready"

# Pre-load the LLM and confirm it is fully GPU-offloaded
echo "→ Pre-loading $LLM_MODEL onto GPU..."
curl -s -X POST "http://localhost:11434/api/generate" \
    -H "Content-Type: application/json" \
    -d "{\"model\":\"$LLM_MODEL\",\"prompt\":\"hello\",\"stream\":false,\"options\":{\"num_predict\":1}}" > /dev/null 2>&1

GPU_OK=false
for i in {1..30}; do
    PS_OUT=$(ollama ps 2>/dev/null || true)
    if echo "$PS_OUT" | grep -q "$LLM_MODEL"; then
        if echo "$PS_OUT" | grep "$LLM_MODEL" | grep -q "100% GPU"; then
            GPU_OK=true
            break
        elif echo "$PS_OUT" | grep "$LLM_MODEL" | grep -qi "CPU"; then
            echo "  ⚠ Model using CPU; retrying ($i/30)..."
            ollama stop "$LLM_MODEL" 2>/dev/null || true
            sleep 2
            curl -s -X POST "http://localhost:11434/api/generate" \
                -H "Content-Type: application/json" \
                -d "{\"model\":\"$LLM_MODEL\",\"prompt\":\"hello\",\"stream\":false,\"options\":{\"num_predict\":1}}" > /dev/null 2>&1
        fi
    fi
    sleep 2
done

if [ "$GPU_OK" = true ]; then
    echo "✓ $LLM_MODEL loaded 100% on GPU"
else
    echo "⚠ Could not confirm 100% GPU offload; check logs/ollama.log"
fi

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
