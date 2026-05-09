#!/bin/bash
# NZ Legal Advisor - Automated RunPod Setup
# Run this INSIDE RunPod Web Terminal
# Usage: curl -fsSL https://raw.githubusercontent.com/1024KBDOTCODOTNZ/redesigned-tribble/setup.sh | bash
# Or: wget -qO- <url> | bash

set -e

echo "════════════════════════════════════════════════════════════════"
echo "  NZ Legal Advisor - Automated Setup"
echo "  RunPod GPU Cloud Deployment"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "This script will:"
echo "  1. Configure GPU (RTX 3090)"
echo "  2. Install Ollama (LLM engine)"
echo "  3. Download AI models (~30GB)"
echo "  4. Create directory structure"
echo "  5. Setup Python environment"
echo ""
echo "Estimated time: 15-20 minutes"
echo ""
read -p "Press Enter to continue or Ctrl+C to cancel..."
echo ""

# ============================================
# STEP 1: System Check
# ============================================
echo "[1/10] System Check..."
echo "----------------------------------------"

# Check GPU
if ! nvidia-smi > /dev/null 2>&1; then
    echo "❌ ERROR: No GPU detected!"
    exit 1
fi

echo "✓ GPU detected:"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader

# Check workspace
if [ ! -d "/workspace" ]; then
    echo "❌ ERROR: /workspace not found!"
    echo "   Make sure Volume Disk is mounted."
    exit 1
fi

echo "✓ Workspace mounted:"
df -h /workspace | tail -1

# Check available space
AVAILABLE=$(df /workspace | tail -1 | awk '{print $4}')
if [ $AVAILABLE -lt 40000000 ]; then  # ~40GB in KB
    echo "⚠️  WARNING: Less than 40GB available on /workspace"
    echo "   Models need ~30GB. Continuing anyway..."
else
    echo "✓ Sufficient disk space"
fi

echo ""

# ============================================
# STEP 2: Setup Ollama
# ============================================
echo "[2/10] Setting up Ollama..."
echo "----------------------------------------"

# Set persistent storage
export OLLAMA_MODELS=/workspace/ollama_models
mkdir -p $OLLAMA_MODELS
echo "✓ Model storage set to: $OLLAMA_MODELS"

# Install Ollama if not exists
if ! command -v ollama &> /dev/null; then
    echo "Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
    echo "✓ Ollama installed"
else
    echo "✓ Ollama already installed"
fi

# Configure for GPU
echo "Configuring GPU acceleration..."
mkdir -p /etc/systemd/system/ollama.service.d
cat > /etc/systemd/system/ollama.service.d/gpu.conf << 'EOF'
[Service]
Environment="OLLAMA_GPU_LAYERS=999"
Environment="CUDA_VISIBLE_DEVICES=0"
Environment="OLLAMA_MODELS=/workspace/ollama_models"
EOF
echo "✓ GPU configuration saved"

# Start Ollama
echo "Starting Ollama service..."
if pgrep -x "ollama" > /dev/null; then
    echo "✓ Ollama already running"
else
    ollama serve &
    sleep 5
    
    # Verify
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "✓ Ollama service started"
    else
        echo "❌ ERROR: Ollama failed to start"
        exit 1
    fi
fi

echo ""

# ============================================
# STEP 3: Download Models
# ============================================
echo "[3/10] Downloading AI Models..."
echo "----------------------------------------"
echo "This will take 10-15 minutes (~30GB)"
echo ""

# Check if models already exist
if ollama list | grep -q "mixtral"; then
    echo "✓ Mixtral already downloaded"
else
    echo "Downloading mixtral (26GB)..."
    ollama pull mixtral:latest
    echo "✓ Mixtral downloaded"
fi

if ollama list | grep -q "nomic-embed-text"; then
    echo "✓ nomic-embed-text already downloaded"
else
    echo "Downloading nomic-embed-text (274MB)..."
    ollama pull nomic-embed-text:latest
    echo "✓ nomic-embed-text downloaded"
fi

echo ""
echo "Installed models:"
ollama list
echo ""

# ============================================
# STEP 4: Create Directory Structure
# ============================================
echo "[4/10] Creating Directory Structure..."
echo "----------------------------------------"

mkdir -p /workspace/nz_legal_rag
cd /workspace/nz_legal_rag

# Create all necessary directories
mkdir -p chroma_db tenant_data logs data secure_data
mkdir -p api core web security ingestion config

echo "✓ Directory structure created:"
ls -la /workspace/nz_legal_rag/
echo ""

# ============================================
# STEP 5: Setup Python Environment
# ============================================
echo "[5/10] Setting up Python Environment..."
echo "----------------------------------------"

# Update packages
apt-get update -qq

# Install Python if needed
if ! command -v python3 &> /dev/null; then
    echo "Installing Python..."
    apt-get install -y -qq python3 python3-pip python3-venv
fi

# Create virtual environment
cd /workspace/nz_legal_rag
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

echo "✓ Python environment ready"
echo ""

# ============================================
# STEP 6: Install Dependencies
# ============================================
echo "[6/10] Installing Python Dependencies..."
echo "----------------------------------------"
echo "This may take 2-3 minutes..."

source venv/bin/activate

pip install -q --upgrade pip

pip install -q \
    fastapi \
    uvicorn \
    streamlit \
    chromadb \
    langchain \
    langchain-community \
    ollama \
    python-multipart \
    pydantic \
    requests

echo "✓ Dependencies installed"
echo ""

# ============================================
# STEP 7: Create Environment File
# ============================================
echo "[7/10] Creating Configuration..."
echo "----------------------------------------"

cat > /workspace/nz_legal_rag/.env << 'EOF'
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

echo "✓ Configuration file created"
echo ""

# ============================================
# STEP 8: Create Startup Script
# ============================================
echo "[8/10] Creating Startup Script..."
echo "----------------------------------------"

cat > /workspace/start_legal_advisor.sh << 'EOF'
#!/bin/bash
# NZ Legal Advisor Startup Script

cd /workspace/nz_legal_rag
source venv/bin/activate
export OLLAMA_MODELS=/workspace/ollama_models

echo "══════════════════════════════════════════════════"
echo "  NZ Legal Advisor - Starting Services"
echo "══════════════════════════════════════════════════"
echo ""

# Check Ollama
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "[1/3] Starting Ollama..."
    ollama serve &
    sleep 5
else
    echo "[1/3] Ollama already running"
fi

# Verify models
echo "[2/3] Checking models..."
ollama list | grep -E "(mixtral|nomic-embed)" || echo "⚠️  Models not found!"

# Check for database
if [ ! -d "chroma_db" ] || [ -z "$(ls -A chroma_db 2>/dev/null)" ]; then
    echo "⚠️  WARNING: No database found in chroma_db/"
    echo "   Upload your database with:"
    echo "   ./upload_to_runpod.sh <ip>:<port>"
fi

# Start API
echo "[3/3] Starting API server..."
python -m api.server &
API_PID=$!
sleep 3

# Start Web UI
echo "Starting Web Interface..."
streamlit run web/streamlit_app.py --server.port 8501 --server.address 0.0.0.0 &
WEB_PID=$!

echo ""
echo "══════════════════════════════════════════════════"
echo "  ✓ Services Starting..."
echo "══════════════════════════════════════════════════"
echo ""
echo "API Server:     http://localhost:8000"
echo "Web Interface:  http://localhost:8501"
echo "API Docs:       http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services"
echo "══════════════════════════════════════════════════"
echo ""

wait
EOF

chmod +x /workspace/start_legal_advisor.sh
echo "✓ Startup script created: /workspace/start_legal_advisor.sh"
echo ""

# ============================================
# STEP 9: Create Helper Scripts
# ============================================
echo "[9/10] Creating Helper Scripts..."
echo "----------------------------------------"

# Backup script
cat > /workspace/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/workspace/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp -r /workspace/nz_legal_rag/chroma_db "$BACKUP_DIR/" 2>/dev/null || true
cp -r /workspace/nz_legal_rag/tenant_data "$BACKUP_DIR/" 2>/dev/null || true
echo "Backup created: $BACKUP_DIR"
EOF
chmod +x /workspace/backup.sh

# Check GPU script
cat > /workspace/check_gpu.sh << 'EOF'
#!/bin/bash
echo "=== GPU Status ==="
nvidia-smi
echo ""
echo "=== Ollama Models ==="
ollama list
echo ""
echo "=== Disk Usage ==="
df -h /workspace
EOF
chmod +x /workspace/check_gpu.sh

echo "✓ Helper scripts created"
echo ""

# ============================================
# STEP 10: Summary
# ============================================
echo "[10/10] Setup Complete!"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "✅ RunPod is ready for NZ Legal Advisor!"
echo ""
echo "Next steps:"
echo ""
echo "1. UPLOAD YOUR CODE:"
echo "   On local machine:"
echo "   ./upload_to_runpod.sh <runpod-ip>:<port>"
echo ""
echo "2. START SERVICES:"
echo "   /workspace/start_legal_advisor.sh"
echo ""
echo "3. CONNECT FROM LOCAL:"
echo "   ./connect_runpod.sh <runpod-ip>:<port>"
echo ""
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Storage Summary:"
du -sh /workspace/ollama_models 2>/dev/null || echo "  Models: Not yet downloaded"
df -h /workspace | tail -1
echo ""
echo "Setup complete at: $(date)"
