export OLLAMA_CONTEXT_LENGTH=4096
#!/bin/bash
# NZ Legal RAG - Background Startup Script for RunPod
# Usage: ./start_background.sh           (starts in background)
#        ./start_background.sh status    (check if running)
#        ./start_background.sh stop      (stop all services)
#        ./start_background.sh logs      (tail all logs)

cd "$(dirname "$0")"

# Load environment
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

API_PORT=${API_PORT:-8000}
WEB_PORT=${WEB_PORT:-8501}
LOG_DIR="$(pwd)/logs"
mkdir -p "$LOG_DIR"

PIDFILE="/tmp/nzlegal_pids.txt"

start_services() {
    echo "Starting NZ Legal RAG in background mode..."
    
    # Activate venv if present
    if [ -d "venv" ]; then
        source venv/bin/activate
    elif [ -d ".venv" ]; then
        source .venv/bin/activate
    fi
    
    # Start Ollama if needed
    if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "  → Starting Ollama..."
        nohup ollama serve > "$LOG_DIR/ollama.log" 2>&1 &
        disown
        sleep 5
    fi
    
    # Kill any existing processes on our ports
    for pid in $(lsof -ti:$API_PORT 2>/dev/null || true); do
        kill -9 "$pid" 2>/dev/null || true
    done
    for pid in $(lsof -ti:$WEB_PORT 2>/dev/null || true); do
        kill -9 "$pid" 2>/dev/null || true
    done
    sleep 1
    
    # Start API with nohup
    echo "  → Starting API on port $API_PORT..."
    nohup python -m api.server > "$LOG_DIR/api.log" 2>&1 &
    API_PID=$!
    disown $API_PID
    
    # Wait for API to be ready
    echo "  → Waiting for API..."
    for i in {1..90}; do
        if curl -s "http://localhost:$API_PORT/health" > /dev/null 2>&1; then
            echo "  ✓ API ready (PID: $API_PID)"
            break
        fi
        if ! kill -0 $API_PID 2>/dev/null; then
            echo "  ✗ API failed to start. Check logs/api.log"
            exit 1
        fi
        sleep 1
    done
    
    # Start Streamlit with nohup
    echo "  → Starting Web UI on port $WEB_PORT..."
    nohup streamlit run web/streamlit_app.py \
        --server.port "$WEB_PORT" \
        --server.address 0.0.0.0 \
        > "$LOG_DIR/web.log" 2>&1 &
    WEB_PID=$!
    disown $WEB_PID
    sleep 3
    
    if kill -0 $WEB_PID 2>/dev/null; then
        echo "  ✓ Web UI ready (PID: $WEB_PID)"
    else
        echo "  ✗ Web UI failed to start. Check logs/web.log"
        exit 1
    fi
    
    # Save PIDs
    echo "$API_PID $WEB_PID" > "$PIDFILE"
    
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "  NZ Legal RAG is running in BACKGROUND"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    echo "  🌐 Web:     http://localhost:$WEB_PORT"
    echo "  🔌 API:     http://localhost:$API_PORT"
    echo "  📚 Docs:    http://localhost:$API_PORT/docs"
    echo ""
    echo "  PIDs: API=$API_PID, Web=$WEB_PID"
    echo "  Logs: ./logs/"
    echo ""
    echo "  You can safely disconnect from RunPod now."
    echo "═══════════════════════════════════════════════════════════════"
}

stop_services() {
    if [ -f "$PIDFILE" ]; then
        read -r API_PID WEB_PID < "$PIDFILE"
        echo "Stopping services..."
        kill "$API_PID" 2>/dev/null || true
        kill "$WEB_PID" 2>/dev/null || true
        sleep 2
        kill -9 "$API_PID" 2>/dev/null || true
        kill -9 "$WEB_PID" 2>/dev/null || true
        rm -f "$PIDFILE"
        echo "✓ Stopped"
    else
        echo "No PID file found. Killing by port..."
        for pid in $(lsof -ti:$API_PORT 2>/dev/null || true); do kill -9 "$pid" 2>/dev/null || true; done
        for pid in $(lsof -ti:$WEB_PORT 2>/dev/null || true); do kill -9 "$pid" 2>/dev/null || true; done
        echo "✓ Done"
    fi
}

check_status() {
    if [ -f "$PIDFILE" ]; then
        read -r API_PID WEB_PID < "$PIDFILE"
        echo "═══════════════════════════════════════════════════════════════"
        echo "  NZ Legal RAG Status"
        echo "═══════════════════════════════════════════════════════════════"
        
        if kill -0 "$API_PID" 2>/dev/null; then
            echo "  API Server:  RUNNING (PID: $API_PID)"
        else
            echo "  API Server:  NOT RUNNING"
        fi
        
        if kill -0 "$WEB_PID" 2>/dev/null; then
            echo "  Web UI:      RUNNING (PID: $WEB_PID)"
        else
            echo "  Web UI:      NOT RUNNING"
        fi
        
        if curl -s "http://localhost:$API_PORT/health" > /dev/null 2>&1; then
            echo "  API Health:  ✓ RESPONDING"
        else
            echo "  API Health:  ✗ NOT RESPONDING"
        fi
        echo "═══════════════════════════════════════════════════════════════"
    else
        echo "No PID file found. Services may not be running."
    fi
}

tail_logs() {
    echo "Tailing logs (Ctrl+C to exit)..."
    tail -f "$LOG_DIR/api.log" "$LOG_DIR/web.log" 2>/dev/null
}

case "${1:-start}" in
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        stop_services
        sleep 2
        start_services
        ;;
    status)
        check_status
        ;;
    logs)
        tail_logs
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs}"
        exit 1
        ;;
esac
