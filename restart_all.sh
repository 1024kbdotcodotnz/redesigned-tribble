#!/bin/bash
# NZ Legal RAG - Full Shutdown & Restart Script (FIXED v2)
# Kills all services, clears resources, and performs a clean restart

set -e

cd /workspace/nz_legal_rag

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
API_PORT=8000
STREAMLIT_PORT=8501
OLLAMA_PORT=11434
MAX_WAIT=30

# FIXED: Ensure logs directory exists
mkdir -p logs

echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  NZ Legal RAG - Full Shutdown & Restart${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo "This script will:"
echo "  1. Stop all running services (API, Streamlit, Ollama)"
echo "  2. Clear ports and resources"
echo "  3. Verify/install Ollama and models"
echo "  4. Start all services fresh"
echo ""

# Function to check if a port is in use
check_port() {
    local port=$1
    if netstat -tlnp 2>/dev/null | grep -q ":$port "; then
        return 0
    elif ss -tlnp 2>/dev/null | grep -q ":$port "; then
        return 0
    else
        return 1
    fi
}

# Function to kill process on port
kill_port() {
    local port=$1
    local pid=$(netstat -tlnp 2>/dev/null | grep ":$port " | awk '{print $7}' | cut -d'/' -f1 | head -1)
    if [ -z "$pid" ]; then
        pid=$(ss -tlnp 2>/dev/null | grep ":$port " | awk '{print $7}' | cut -d'=' -f2 | cut -d',' -f1 | head -1)
    fi
    if [ -n "$pid" ] && [ "$pid" != "-" ] && [ "$pid" -gt 0 ] 2>/dev/null; then
        kill -9 $pid 2>/dev/null || true
        echo "  Killed process $pid on port $port"
    fi
}

# ============================================
# PHASE 1: SHUTDOWN
# ============================================
echo -e "${YELLOW}[PHASE 1/4] Stopping all services...${NC}"
echo ""

# Stop Streamlit
echo "Stopping Streamlit..."
pkill -9 -f "streamlit run" 2>/dev/null || true
sleep 1
if check_port $STREAMLIT_PORT; then
    kill_port $STREAMLIT_PORT
fi
echo -e "  ${GREEN}✓${NC} Streamlit stopped"

# Stop API server
echo "Stopping API server..."
pkill -9 -f "api.server" 2>/dev/null || true
pkill -9 -f "uvicorn" 2>/dev/null || true
pkill -9 -f "python.*8000" 2>/dev/null || true
sleep 1
if check_port $API_PORT; then
    kill_port $API_PORT
fi
echo -e "  ${GREEN}✓${NC} API server stopped"

# Stop Ollama
echo "Stopping Ollama..."
pkill -9 -f "ollama serve" 2>/dev/null || true
sleep 1
if check_port $OLLAMA_PORT; then
    kill_port $OLLAMA_PORT
fi
echo -e "  ${GREEN}✓${NC} Ollama stopped"

# Kill any remaining Python processes
echo "Cleaning up remaining processes..."
pkill -9 -f "python.*nz_legal" 2>/dev/null || true
sleep 1

# Force kill any lingering processes on our ports
echo "Force clearing ports..."
for port in $API_PORT $STREAMLIT_PORT $OLLAMA_PORT; do
    fuser -k ${port}/tcp 2>/dev/null || true
done

echo ""
echo -e "${GREEN}✓ All services stopped${NC}"
echo ""

# ============================================
# PHASE 2: VERIFY CLEAN STATE
# ============================================
echo -e "${YELLOW}[PHASE 2/4] Verifying clean state...${NC}"
echo ""

sleep 2

# Check ports are clear
ports_clear=true
for port in $API_PORT $STREAMLIT_PORT $OLLAMA_PORT; do
    if check_port $port; then
        echo -e "  ${RED}✗${NC} Port $port still in use"
        ports_clear=false
    else
        echo -e "  ${GREEN}✓${NC} Port $port is clear"
    fi
done

if [ "$ports_clear" = false ]; then
    echo ""
    echo -e "${RED}Warning: Some ports still in use. Attempting force kill...${NC}"
    pkill -9 python 2>/dev/null || true
    pkill -9 ollama 2>/dev/null || true
    sleep 2
fi

# Verify Chroma DB exists
if [ ! -d "/workspace/chroma_db_fresh" ]; then
    echo -e "  ${YELLOW}⚠${NC} Chroma DB not found at /workspace/chroma_db_fresh"
    echo "    Creating empty database directory..."
    mkdir -p /workspace/chroma_db_fresh
else
    echo -e "  ${GREEN}✓${NC} Chroma DB found"
fi

echo ""
echo -e "${GREEN}✓ System is clean${NC}"
echo ""

# ============================================
# PHASE 3: OLLAMA SETUP
# ============================================
echo -e "${YELLOW}[PHASE 3/4] Setting up Ollama...${NC}"
echo ""

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo "Ollama not found. Installing..."
    curl -fsSL https://ollama.com/install.sh | sh
    echo -e "  ${GREEN}✓${NC} Ollama installed"
else
    echo -e "  ${GREEN}✓${NC} Ollama already installed"
fi

# Export OLLAMA_CONTEXT_LENGTH
export OLLAMA_CONTEXT_LENGTH=4096

# Start Ollama server
echo "Starting Ollama server..."
nohup ollama serve > logs/ollama.log 2>&1 &
OLLAMA_PID=$!
echo "  Ollama PID: $OLLAMA_PID"

# Wait for Ollama to be ready
echo "Waiting for Ollama server..."
for i in $(seq 1 $MAX_WAIT); do
    if curl -s localhost:$OLLAMA_PORT/api/tags > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} Ollama server ready"
        break
    fi
    sleep 1
    echo -n "."
done
echo ""

# Check and pull required models
EMBEDDING_MODEL="${EMBEDDING_MODEL:-nomic-embed-text:latest}"
LLM_MODEL="${LLM_MODEL:-deepseek-r1}"

echo "Checking required models..."
REQUIRED_MODELS=("$EMBEDDING_MODEL" "$LLM_MODEL")
for model in "${REQUIRED_MODELS[@]}"; do
    if curl -s localhost:$OLLAMA_PORT/api/tags | grep -q "\"name\":\"$model\""; then
        echo -e "  ${GREEN}✓${NC} $model installed"
    else
        echo "  Pulling $model..."
        curl -s -X POST localhost:$OLLAMA_PORT/api/pull             -H "Content-Type: application/json"             -d "{\"name\":\"$model\"}" > /dev/null 2>&1 &
        echo "    (pulling in background - may take several minutes)"
    fi
done

echo ""
echo -e "${GREEN}✓ Ollama setup complete${NC}"
echo ""

# ============================================
# PHASE 4: START SERVICES
# ============================================
echo -e "${YELLOW}[PHASE 4/4] Starting application services...${NC}"
echo ""

# Load virtual environment only if it exists
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    echo -e "  ${GREEN}✓${NC} Virtual environment activated"
else
    echo -e "  ${YELLOW}⚠${NC} No .venv found, using system Python"
fi

# Set environment variables
export EMBEDDING_MODEL="$EMBEDDING_MODEL"
export LLM_MODEL="$LLM_MODEL"
export OLLAMA_HOST="http://localhost:$OLLAMA_PORT"
export CHROMA_DB_PATH="/workspace/chroma_db_fresh"
export CHROMADB_PATH="/workspace/chroma_db_fresh"
export CHROMA_PERSIST_DIR="/workspace/chroma_db_fresh"
export ADMIN_API_KEY=eeb7ddacf4f3d4ed69aca0551f14d37f20d27a2c84d0a649ecc2be78ce09ece1
export API_HOST="0.0.0.0"
export API_PORT="8000"
export TENANT_DATA_PATH="./tenant_data"
export DEMO_DATA_PATH="./demo_sessions"
export DEMO_SESSION_ROOT="./temp_sessions"

echo "Environment:"
echo "  EMBEDDING_MODEL=$EMBEDDING_MODEL"
echo "  LLM_MODEL=$LLM_MODEL"
echo "  CHROMA_DB_PATH=$CHROMA_DB_PATH"

# Start API server
echo "Starting API server on port $API_PORT..."
nohup python3 -m uvicorn api.server:app --host 0.0.0.0 --port $API_PORT --log-level info > logs/api.log 2>&1 &
API_PID=$!
echo "  API PID: $API_PID"

# Wait for API to be ready
echo "Waiting for API server..."
for i in $(seq 1 $MAX_WAIT); do
    if curl -s localhost:$API_PORT/health > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} API server ready"
        break
    fi
    sleep 1
    echo -n "."
done
echo ""

# Start Streamlit
# FIXED: streamlit_app.py is in web/ directory
STREAMLIT_APP="web/streamlit_app.py"
if [ ! -f "$STREAMLIT_APP" ]; then
    echo -e "  ${RED}✗${NC} $STREAMLIT_APP not found!"
    echo "    Looking for streamlit_app.py in other locations..."
    if [ -f "streamlit_app.py" ]; then
        STREAMLIT_APP="streamlit_app.py"
        echo -e "  ${YELLOW}⚠${NC} Found at repo root, using that"
    else
        echo -e "  ${RED}✗${NC} Cannot find streamlit_app.py - aborting"
        exit 1
    fi
fi

echo "Starting Streamlit on port $STREAMLIT_PORT (using $STREAMLIT_APP)..."
nohup streamlit run $STREAMLIT_APP     --server.port=$STREAMLIT_PORT     --server.address=0.0.0.0     --server.headless=true     > logs/streamlit.log 2>&1 &
STREAMLIT_PID=$!
echo "  Streamlit PID: $STREAMLIT_PID"

# Wait for Streamlit
echo "Waiting for Streamlit server..."
for i in $(seq 1 $MAX_WAIT); do
    if curl -s localhost:$STREAMLIT_PORT > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} Streamlit ready"
        break
    fi
    sleep 1
    echo -n "."
done
echo ""

# ============================================
# FINAL STATUS
# ============================================
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✓ RESTART COMPLETE!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Get IP for display
IP=$(hostname -I | awk '{print $1}')

echo "Service URLs:"
echo -e "  ${BLUE}• Streamlit:${NC} http://$IP:$STREAMLIT_PORT"
echo -e "  ${BLUE}• API:${NC}       http://$IP:$API_PORT"
echo -e "  ${BLUE}• API Docs:${NC}  http://$IP:$API_PORT/docs"
echo ""

echo "Process IDs:"
echo "  • Ollama:    $OLLAMA_PID"
echo "  • API:       $API_PID"
echo "  • Streamlit: $STREAMLIT_PID"
echo ""

echo "Log files:"
echo "  • Ollama:    tail -f logs/ollama.log"
echo "  • API:       tail -f logs/api.log"
echo "  • Streamlit: tail -f logs/streamlit.log"
echo ""

# Final health check
echo "Performing health check..."
if curl -s localhost:$API_PORT/health > /dev/null 2>&1; then
    HEALTH_STATUS=$(curl -s localhost:$API_PORT/health | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','unknown'))" 2>/dev/null || echo "unknown")
    echo -e "  ${GREEN}✓${NC} API healthy - status: $HEALTH_STATUS"
else
    echo -e "  ${RED}✗${NC} API not responding"
fi

if curl -s localhost:$OLLAMA_PORT/api/tags > /dev/null 2>&1; then
    MODEL_COUNT=$(curl -s localhost:$OLLAMA_PORT/api/tags | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('models',[])))" 2>/dev/null || echo "0")
    echo -e "  ${GREEN}✓${NC} Ollama healthy - $MODEL_COUNT models available"
else
    echo -e "  ${RED}✗${NC} Ollama not responding"
fi

echo ""
echo "Useful commands:"
echo "  • View logs:     tail -f logs/*.log"
echo "  • Stop all:      pkill -9 -f 'ollama|uvicorn|streamlit'"
echo "  • Health check:  curl -s localhost:8000/health"
echo ""
