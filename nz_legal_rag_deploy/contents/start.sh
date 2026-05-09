#!/bin/bash
# NZ Legal RAG Startup Script

cd "$(dirname "$0")"

# Load environment
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Check if running in virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    if [ -d "venv" ]; then
        echo "Activating virtual environment..."
        source venv/bin/activate
    fi
fi

# Check Ollama
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "⚠️  Ollama not running. Please start it first:"
    echo "   ollama serve"
    exit 1
fi

echo "✓ Ollama is running"
echo "✓ Models available:"
ollama list | grep -E "(mixtral|nomic-embed-text|mistral|llama3.1)"

echo ""
echo "Starting NZ Legal RAG..."

# Create necessary directories
mkdir -p data logs chroma_db tenant_data secure_data

# Start API server
echo ""
echo "🚀 Starting API server on port ${API_PORT:-8000}..."
python -m api.server &
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

# Start web interface
echo ""
echo "🌐 Starting web interface on port 8501..."
streamlit run web/streamlit_app.py --server.port 8501 &
WEB_PID=$!

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  NZ Legal RAG is running!"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "  🌐 Web Interface:  http://localhost:8501"
echo "  🔌 API:            http://localhost:${API_PORT:-8000}"
echo "  📚 API Docs:       http://localhost:${API_PORT:-8000}/docs"
echo ""
echo "  Press Ctrl+C to stop"
echo ""
echo "═══════════════════════════════════════════════════════════════"

# Wait for interrupt
trap "echo ''; echo 'Shutting down...'; kill $API_PID $WEB_PID 2>/dev/null; exit" INT
wait
