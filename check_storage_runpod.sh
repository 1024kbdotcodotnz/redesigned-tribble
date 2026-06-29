#!/bin/bash
# Check RunPod storage configuration (for RunPod.io hosted SSH)
# Usage: ./check_storage_runpod.sh [ssh-host] [identity-file]

# Default values from RUNPOD_CONNECT.md
DEFAULT_SSH_HOST="hfm6dv73af3es0-64410b2f@ssh.runpod.io"
DEFAULT_IDENTITY="~/.ssh/id_ed25519"

SSH_HOST="${1:-$DEFAULT_SSH_HOST}"
IDENTITY_FILE="${2:-$DEFAULT_IDENTITY}"

echo "══════════════════════════════════════════════════"
echo "  NZ Legal Advisor - Storage Check"
echo "══════════════════════════════════════════════════"
echo ""

# Expand tilde in identity file path
IDENTITY_FILE="${IDENTITY_FILE/#\~/$HOME}"

# Function to test SSH connection
test_ssh_connection() {
    local host="$1"
    local id_file="$2"
    local extra_opts="$3"
    
    if [ -n "$id_file" ] && [ -f "$id_file" ]; then
        ssh -i "$id_file" -o ConnectTimeout=5 -o StrictHostKeyChecking=accept-new $extra_opts "$host" "echo 'connected'" 2>/dev/null
    else
        ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=accept-new $extra_opts "$host" "echo 'connected'" 2>/dev/null
    fi
}

# Try multiple connection methods
CONNECTED=false
ACTIVE_SSH_CMD=""
ACTIVE_IDENTITY=""

echo "Testing connection methods..."
echo ""

# Method 1: Try 'ssh runpod' (using SSH config)
echo "  [1/3] Trying 'ssh runpod' (SSH config)..."
if test_ssh_connection "runpod" "" "" >/dev/null; then
    echo "      ✓ Success!"
    CONNECTED=true
    ACTIVE_SSH_CMD="runpod"
    ACTIVE_IDENTITY=""
else
    echo "      ✗ Failed"
fi

# Method 2: Try explicit host with identity file
if [ "$CONNECTED" = false ]; then
    echo "  [2/3] Trying '$SSH_HOST' with identity..."
    if test_ssh_connection "$SSH_HOST" "$IDENTITY_FILE" "" >/dev/null; then
        echo "      ✓ Success!"
        CONNECTED=true
        ACTIVE_SSH_CMD="$SSH_HOST"
        ACTIVE_IDENTITY="$IDENTITY_FILE"
    else
        echo "      ✗ Failed"
    fi
fi

# Method 3: Try with SSH agent disabled (forces key file use)
if [ "$CONNECTED" = false ]; then
    echo "  [3/3] Trying with IdentitiesOnly..."
    if ssh -i "$IDENTITY_FILE" -o ConnectTimeout=5 -o StrictHostKeyChecking=accept-new -o IdentitiesOnly=yes "$SSH_HOST" "echo 'connected'" 2>/dev/null; then
        echo "      ✓ Success!"
        CONNECTED=true
        ACTIVE_SSH_CMD="$SSH_HOST"
        ACTIVE_IDENTITY="$IDENTITY_FILE"
    else
        echo "      ✗ Failed"
    fi
fi

if [ "$CONNECTED" = false ]; then
    echo ""
    echo "❌ Cannot connect to RunPod"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Check if the pod is RUNNING at https://www.runpod.io/console/pods"
    echo "  2. If pod was restarted, the SSH host may have changed"
    echo "  3. Verify your SSH key: ls -la ~/.ssh/id_ed25519"
    echo "  4. Try updating the host from RunPod console and run:"
    echo "     ./check_storage_runpod.sh new-host@ssh.runpod.io"
    echo "  5. Use Web Terminal as alternative (see below)"
    echo ""
    echo "══════════════════════════════════════════════════"
    echo "  Web Terminal Alternative (No SSH needed)"
    echo "══════════════════════════════════════════════════"
    echo ""
    echo "  1. Go to https://www.runpod.io/console/pods"
    echo "  2. Click your pod → 'Web Terminal'"
    echo "  3. Run these commands:"
    echo ""
    echo "     df -h | grep -E '(Filesystem|workspace|volume)'"
    echo "     du -sh /workspace/"
    echo "     ls -la /workspace/"
    echo ""
    exit 1
fi

echo ""
echo "Connected! Checking storage configuration..."
echo ""

# Build SSH command
if [ -n "$ACTIVE_IDENTITY" ]; then
    SSH_BASE="ssh -i \"$ACTIVE_IDENTITY\""
else
    SSH_BASE="ssh"
fi

# Run storage checks
$SSH_BASE "$ACTIVE_SSH_CMD" '
    echo "=== DISK MOUNTS ==="
    df -h | grep -E "(Filesystem|workspace|runpod-volume)"
    
    echo ""
    echo "=== WORKSPACE LOCATION ==="
    if [ -L /workspace ]; then
        echo "/workspace is a symlink to: $(readlink -f /workspace)"
    else
        echo "/workspace is a regular directory"
    fi
    
    echo ""
    echo "=== PERSISTENCE CHECK ==="
    if [ -f /workspace/README.txt ]; then
        echo "✓ Volume persistence: OK"
        cat /workspace/README.txt
    else
        echo "⚠️ Volume persistence: UNCLEAR"
        echo "  /workspace/README.txt not found"
    fi
    
    echo ""
    echo "=== STORAGE USAGE ==="
    echo "Workspace usage:"
    du -sh /workspace/ 2>/dev/null | head -1
    
    if [ -d /workspace/nz_legal_rag ]; then
        echo ""
        echo "NZ Legal Advisor:"
        du -sh /workspace/nz_legal_rag/ 2>/dev/null | head -1
    fi
    
    if [ -d /workspace/ollama_models ]; then
        echo ""
        echo "Ollama models:"
        du -sh /workspace/ollama_models/ 2>/dev/null | head -1
    fi
    
    echo ""
    echo "=== AVAILABLE SPACE ==="
    df -h | grep -E "/workspace|/runpod-volume" | awk "{print \"Available: \" \$4 \" (\" \$5 \" used)\"}"
'

echo ""
echo "══════════════════════════════════════════════════"
echo ""
echo "Storage Recommendations:"
echo ""

$SSH_BASE "$ACTIVE_SSH_CMD" '
    VOL_SIZE=$(df -h /workspace 2>/dev/null | tail -1 | awk "{print \$2}")
    if [ -z "$VOL_SIZE" ]; then
        echo "❌ CRITICAL: No volume disk detected!"
        echo "   Your database will be LOST when pod stops!"
        echo ""
        echo "   FIX: Deploy new pod with Volume Disk (50GB+)"
    else
        SIZE_NUM=$(echo $VOL_SIZE | sed "s/G//")
        if [ "$SIZE_NUM" -lt 30 ] 2>/dev/null; then
            echo "⚠️  WARNING: Volume is only ${VOL_SIZE}"
            echo "   May not fit Ollama models (need ~30GB)"
            echo ""
            echo "   RECOMMENDATION: Increase to 50GB Volume"
        else
            echo "✓ Volume size: ${VOL_SIZE} - GOOD"
        fi
        
        # Check if models are on volume
        if [ -d /workspace/ollama_models ] && [ $(du -s /workspace/ollama_models 2>/dev/null | cut -f1) -gt 100000 ]; then
            echo "✓ Ollama models on Volume - GOOD"
        else
            echo "⚠️  Ollama models not on Volume or not installed"
        fi
    fi
'

echo ""
