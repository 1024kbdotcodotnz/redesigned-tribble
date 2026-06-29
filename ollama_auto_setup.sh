#!/bin/bash
# Ollama Auto-Recovery Script
# Ensures Ollama is installed and required models are available
# Run this on system startup or when models are missing

set -e

# Configuration
OLLAMA_HOST="${OLLAMA_HOST:-http://localhost:11434}"
LLM_MODEL="${LLM_MODEL:-qwen2.5:14b}"
EMBEDDING_MODEL="${EMBEDDING_MODEL:-nomic-embed-text:latest}"
REQUIRED_MODELS=("$EMBEDDING_MODEL" "$LLM_MODEL")
MAX_WAIT=60

echo "═══════════════════════════════════════════════════════════════"
echo "  Ollama Auto-Recovery"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Function to check if Ollama is installed
check_ollama_installed() {
    if command -v ollama &> /dev/null; then
        echo "✓ Ollama is installed"
        return 0
    else
        echo "✗ Ollama not found"
        return 1
    fi
}

# Function to install Ollama
install_ollama() {
    echo "Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
    echo "✓ Ollama installed"
}

# Function to start Ollama server
start_ollama_server() {
    echo "Starting Ollama server..."

    # Configure for full GPU offload
    export OLLAMA_MODELS=/workspace/ollama_models
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

    # Stop systemd-managed instance if present
    systemctl stop ollama 2>/dev/null || true

    # Kill any existing Ollama processes
    pkill -9 -f "ollama serve" 2>/dev/null || true
    sleep 1

    # Start Ollama in background
    nohup ollama serve > /tmp/ollama.log 2>&1 &

    # Wait for server to be ready
    echo "Waiting for Ollama server to start..."
    for i in $(seq 1 $MAX_WAIT); do
        if curl -s "$OLLAMA_HOST/api/tags" > /dev/null 2>&1; then
            echo "✓ Ollama server is ready"
            return 0
        fi
        sleep 1
        echo -n "."
    done
    echo ""
    echo "✗ Timeout waiting for Ollama server"
    return 1
}

# Function to check if a model is installed
check_model() {
    local model=$1
    if curl -s "$OLLAMA_HOST/api/tags" 2>/dev/null | grep -q "\"name\":\"$model\""; then
        return 0
    else
        return 1
    fi
}

# Function to pull a model
pull_model() {
    local model=$1
    echo "Pulling model: $model..."
    
    # Pull with progress
    curl -s -X POST "$OLLAMA_HOST/api/pull" \
        -H "Content-Type: application/json" \
        -d "{\"name\":\"$model\"}" | while read -r line; do
        if echo "$line" | grep -q '"status":"success"'; then
            echo ""
            echo "✓ Model $model installed successfully"
            break
        fi
        echo -n "."
    done
    echo ""
}

# Function to get model info
get_model_info() {
    local model=$1
    local size=$(curl -s "$OLLAMA_HOST/api/show" \
        -H "Content-Type: application/json" \
        -d "{\"name\":\"$model\"}" 2>/dev/null | \
        python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('details', {}).get('parameter_size', 'unknown'))" 2>/dev/null || echo "unknown")
    echo "$size"
}

# Main execution
main() {
    # Step 1: Check/Install Ollama
    if ! check_ollama_installed; then
        install_ollama
    fi
    
    # Step 2: Start Ollama server
    if ! curl -s "$OLLAMA_HOST/api/tags" > /dev/null 2>&1; then
        start_ollama_server
    else
        echo "✓ Ollama server is already running"
    fi
    
    # Step 3: Check and install required models
    echo ""
    echo "Checking required models..."
    local missing_models=()
    
    for model in "${REQUIRED_MODELS[@]}"; do
        if check_model "$model"; then
            local size=$(get_model_info "$model")
            echo "  ✓ $model ($size)"
        else
            echo "  ✗ $model (missing)"
            missing_models+=("$model")
        fi
    done
    
    # Pull missing models
    if [ ${#missing_models[@]} -gt 0 ]; then
        echo ""
        echo "Installing missing models..."
        for model in "${missing_models[@]}"; do
            pull_model "$model"
        done
    else
        echo ""
        echo "✓ All required models are installed"
    fi
    
    # Pre-load the LLM and verify full GPU offload
    echo ""
    echo "Pre-loading $LLM_MODEL onto GPU..."
    curl -s -X POST "$OLLAMA_HOST/api/generate" \
        -H "Content-Type: application/json" \
        -d "{\"model\":\"$LLM_MODEL\",\"prompt\":\"hello\",\"stream\":false,\"options\":{\"num_predict\":1}}" > /dev/null 2>&1

    GPU_OK=false
    for i in $(seq 1 30); do
        PS_OUT=$(ollama ps 2>/dev/null || true)
        if echo "$PS_OUT" | grep -q "$LLM_MODEL"; then
            if echo "$PS_OUT" | grep "$LLM_MODEL" | grep -q "100% GPU"; then
                GPU_OK=true
                break
            elif echo "$PS_OUT" | grep "$LLM_MODEL" | grep -qi "CPU"; then
                echo "  ⚠ Model using CPU; retrying ($i/30)..."
                ollama stop "$LLM_MODEL" 2>/dev/null || true
                sleep 2
                curl -s -X POST "$OLLAMA_HOST/api/generate" \
                    -H "Content-Type: application/json" \
                    -d "{\"model\":\"$LLM_MODEL\",\"prompt\":\"hello\",\"stream\":false,\"options\":{\"num_predict\":1}}" > /dev/null 2>&1
            fi
        fi
        sleep 2
    done

    # Final verification
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "  Final Status"
    echo "═══════════════════════════════════════════════════════════════"
    curl -s "$OLLAMA_HOST/api/tags" | python3 -m json.tool 2>/dev/null | grep '"name"' || echo "  Models: $(curl -s $OLLAMA_HOST/api/tags 2>/dev/null | grep -o '"name":"[^"]*"' | wc -l) installed"
    if [ "$GPU_OK" = true ]; then
        echo "  ✓ $LLM_MODEL loaded 100% on GPU"
    else
        echo "  ⚠ Could not confirm 100% GPU offload; check /tmp/ollama.log"
    fi
    echo ""
    echo "✓ Ollama auto-recovery complete!"
}

# Run main function
main "$@"
