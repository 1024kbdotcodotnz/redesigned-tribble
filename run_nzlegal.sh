#!/bin/bash
# NZ Legal RAG - Run Script (using existing environment)

cd "$(dirname "$0")"

# Use existing chat-with-documents venv
VENV_PATH="/home/owner/chat-with-documents/venv"
if [ -d "$VENV_PATH" ]; then
    echo "Using existing virtual environment: $VENV_PATH"
    source "$VENV_PATH/bin/activate"
else
    echo "Virtual environment not found at $VENV_PATH"
    exit 1
fi

# Check Ollama
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "⚠️  Ollama not running!"
    echo "Start it with: ollama serve"
    exit 1
fi

echo "✓ Ollama is running"

# Create necessary directories
mkdir -p data/{legislation,case_law,police_manual,court_rules}
mkdir -p chroma_db tenant_data secure_data logs

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cat > .env << 'EOF'
CHROMA_DB_PATH=./chroma_db
TENANT_DATA_PATH=./tenant_data
OLLAMA_HOST=http://localhost:11434
EMBEDDING_MODEL=nomic-embed-text
LLM_MODEL=mixtral:latest
API_HOST=0.0.0.0
API_PORT=8000
ADMIN_API_KEY=dev-key-change-in-production
ENABLE_CONFIDENTIAL_DOCS=true
ENABLE_API=true
LOG_LEVEL=INFO
EOF
    echo "✓ Created .env"
fi

# Export environment
export $(grep -v '^#' .env | xargs)

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  Starting NZ Legal RAG"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Check if we should start API or run CLI
case "${1:-all}" in
    api)
        echo "🚀 Starting API server..."
        python -m api.server
        ;;
    web)
        echo "🌐 Starting web interface..."
        streamlit run web/streamlit_app.py --server.port 8501
        ;;
    cli)
        shift
        echo "🔧 Running CLI..."
        python -m core.rag_engine "$@"
        ;;
    all|*)
        echo "🚀 Starting API server on port 8000..."
        python -m api.server &
        API_PID=$!
        
        echo "⏳ Waiting for API..."
        for i in {1..30}; do
            if curl -s http://localhost:8000/health > /dev/null 2>&1; then
                echo "✓ API ready"
                break
            fi
            sleep 1
        done
        
        echo "🌐 Starting web interface on port 8501..."
        streamlit run web/streamlit_app.py --server.port 8501 &
        WEB_PID=$!
        
        echo ""
        echo "═══════════════════════════════════════════════════════════════"
        echo "  NZ Legal RAG is running!"
        echo "═══════════════════════════════════════════════════════════════"
        echo ""
        echo "  🌐 Web:     http://localhost:8501"
        echo "  🔌 API:     http://localhost:8000"
        echo "  📚 Docs:    http://localhost:8000/docs"
        echo ""
        echo "  Press Ctrl+C to stop"
        echo ""
        
        trap "kill $API_PID $WEB_PID 2>/dev/null; exit" INT
        wait
        ;;
esac
