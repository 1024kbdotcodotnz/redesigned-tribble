#!/bin/bash
# Ollama Setup Script with Persistent Storage
# For RunPod / cloud environments

set -e

echo "🔧 Setting up Ollama with persistent storage..."

# Set persistent storage for models
export OLLAMA_MODELS=/workspace/ollama_models
mkdir -p $OLLAMA_MODELS

echo "📁 Models directory: $OLLAMA_MODELS"

# Check if Ollama is already installed
if ! command -v ollama &> /dev/null; then
    echo "⬇️  Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
    echo "✓ Ollama installed"
else
    echo "✓ Ollama already installed ($(ollama --version 2>/dev/null | head -1))"
fi

# Create a startup script for convenience
cat > /workspace/start_ollama.sh << 'EOF'
#!/bin/bash
export OLLAMA_MODELS=/workspace/ollama_models

# Kill any existing Ollama processes
pkill -f "ollama serve" 2>/dev/null || true
sleep 1

echo "🚀 Starting Ollama server..."
ollama serve &

# Wait for server to be ready
echo "⏳ Waiting for Ollama to start..."
for i in {1..30}; do
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "✓ Ollama is ready!"
        ollama list
        exit 0
    fi
    sleep 1
done

echo "✗ Ollama failed to start"
exit 1
EOF

chmod +x /workspace/start_ollama.sh

echo ""
echo "═══════════════════════════════════════════════════"
echo "  ✓ Ollama setup complete!"
echo "═══════════════════════════════════════════════════"
echo ""
echo "📂 Models stored in: $OLLAMA_MODELS"
echo ""
echo "Quick start:"
echo "  /workspace/start_ollama.sh     # Start the server"
echo "  ollama run llama3.1            # Run a model"
echo "  ollama pull mistral            # Download a model"
echo "  ollama list                    # List available models"
echo ""
