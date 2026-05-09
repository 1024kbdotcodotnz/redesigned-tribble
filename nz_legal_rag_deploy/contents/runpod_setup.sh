#!/bin/bash
# Solo Practitioner Setup Script for RunPod
# NZ Legal Advisor - RunPod Deployment

set -e

echo "══════════════════════════════════════════════════"
echo "  NZ Legal Advisor - Solo Practitioner Setup"
echo "══════════════════════════════════════════════════"

# Update system
echo "[1/8] Updating system..."
apt-get update -qq && apt-get install -y -qq curl wget git nano htop screen

# Check if running on RunPod Volume
if [ -d "/runpod-volume" ]; then
    echo "✓ RunPod Volume detected"
    # Ensure /workspace is linked to volume
    if [ ! -L "/workspace" ]; then
        mkdir -p /runpod-volume/workspace
        ln -sf /runpod-volume/workspace /workspace
    fi
else
    echo "Note: Not running on RunPod or no volume attached"
    mkdir -p /workspace
fi

# Set Ollama models to use Volume Disk (persistent)
export OLLAMA_MODELS=/workspace/ollama_models
mkdir -p $OLLAMA_MODELS

# Install Ollama
echo "[2/8] Installing Ollama..."
curl -fsSL https://ollama.com/install.sh | sh

# Configure Ollama for GPU and Volume storage
echo "[3/8] Configuring Ollama for RTX 3090..."
mkdir -p /etc/systemd/system/ollama.service.d
cat > /etc/systemd/system/ollama.service.d/gpu.conf << 'EOF'
[Service]
Environment="OLLAMA_GPU_LAYERS=999"
Environment="CUDA_VISIBLE_DEVICES=0"
Environment="OLLAMA_NUM_PARALLEL=4"
Environment="OLLAMA_MODELS=/workspace/ollama_models"
EOF

# Start Ollama
echo "[4/8] Starting Ollama..."
ollama serve &
sleep 10

# Pull models
echo "[5/8] Downloading AI models (~30GB)..."
echo "This may take 10-15 minutes..."
ollama pull nomic-embed-text:latest
ollama pull mixtral:latest
# Alternative smaller model for faster responses:
# ollama pull llama3.1:8b

echo "✓ Models ready"
ollama list

# Setup Python environment
echo "[6/8] Setting up Python..."
apt-get install -y -qq python3-pip python3-venv

# Create app directory on Volume (persistent)
echo "[7/8] Preparing application directory on Volume Disk..."
mkdir -p /workspace/nz_legal_rag
cd /workspace/nz_legal_rag

# Create a marker file to confirm volume persistence
echo "Volume Disk mounted at /workspace" > /workspace/README.txt
date >> /workspace/README.txt

echo "✓ Using Volume Disk at /workspace (persistent storage)"

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies (will be done after code upload)
pip install -q fastapi uvicorn streamlit chromadb langchain ollama

# Create startup script
echo "[8/8] Creating startup scripts..."
cat > /workspace/start_legal_advisor.sh << 'EOFSCRIPT'
#!/bin/bash
cd /workspace/nz_legal_rag
source venv/bin/activate

echo "Starting NZ Legal Advisor..."
echo "═══════════════════════════════════════"

# Start Ollama in background
if ! pgrep -x "ollama" > /dev/null; then
    echo "Starting Ollama..."
    ollama serve &
    sleep 5
fi

# Check if API server exists
if [ -f "api/server.py" ]; then
    echo "Starting API server on port 8000..."
    python -m api.server &
    API_PID=$!
    sleep 5
    
    echo "Starting Web Interface on port 8501..."
    streamlit run web/streamlit_app.py --server.port 8501 --server.address 0.0.0.0 &
    WEB_PID=$!
    
    echo ""
    echo "═══════════════════════════════════════"
    echo "  NZ Legal Advisor is running!"
    echo "═══════════════════════════════════════"
    echo ""
    echo "  API:       http://localhost:8000"
    echo "  Web UI:    http://localhost:8501"
    echo "  API Docs:  http://localhost:8000/docs"
    echo ""
    echo "  Press Ctrl+C to stop"
    echo "═══════════════════════════════════════"
    
    wait
else
    echo "⚠️  Application code not found."
    echo "Please upload nz_legal_rag folder to /workspace/"
fi
EOFSCRIPT

chmod +x /workspace/start_legal_advisor.sh

echo ""
echo "══════════════════════════════════════════════════"
echo "  ✓ Setup Complete!"
echo "══════════════════════════════════════════════════"
echo ""
echo "Next steps:"
echo "1. Upload your nz_legal_rag code to /workspace/"
echo "2. Upload your chroma_db to /workspace/nz_legal_rag/"
echo "3. Run: /workspace/start_legal_advisor.sh"
echo ""
echo "GPU Status:"
nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader
echo ""
