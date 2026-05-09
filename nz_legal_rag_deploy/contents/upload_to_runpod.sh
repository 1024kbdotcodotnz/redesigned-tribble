#!/bin/bash
# Upload NZ Legal Advisor to RunPod
# Run this from your local machine

RUNPOD_ADDR="$1"

if [ -z "$RUNPOD_ADDR" ]; then
    echo "Usage: ./upload_to_runpod.sh <your-runpod-ip>[:port]"
    echo "Examples:"
    echo "  ./upload_to_runpod.sh 194.36.144.12"
    echo "  ./upload_to_runpod.sh 213.192.2.88:40141"
    exit 1
fi

# Parse IP and port
RUNPOD_IP=$(echo "$RUNPOD_ADDR" | cut -d: -f1)
RUNPOD_PORT=$(echo "$RUNPOD_ADDR" | grep -o ':[0-9]*$' | tr -d ':')

# Default to port 22 if not specified
if [ -z "$RUNPOD_PORT" ]; then
    RUNPOD_PORT=22
fi

SSH_OPTS="-P $RUNPOD_PORT"
if [ "$RUNPOD_PORT" = "22" ]; then
    SSH_OPTS=""
fi

echo "Uploading NZ Legal Advisor to RunPod at $RUNPOD_IP (port $RUNPOD_PORT)..."
echo ""
echo "⚠️  IMPORTANT: Make sure your RunPod has Volume Disk enabled!"
echo "   - Container Disk: LOST when pod stops (code only)"
echo "   - Volume Disk: PERSISTS (database + models)"
echo ""
echo "   Recommended: 50GB Volume Disk + 20GB Container Disk"
echo ""
read -p "Press Enter to continue or Ctrl+C to cancel..."

# Create exclude list
EXCLUDES="--exclude=venv --exclude=__pycache__ --exclude='*.pyc' --exclude='*.log'"

# Upload main code (without venv)
echo "[1/3] Uploading application code..."
rsync -avz -e "ssh -p $RUNPOD_PORT" --progress $EXCLUDES \
    /home/owner/nz_legal_rag/ \
    root@$RUNPOD_IP:/workspace/nz_legal_rag/

# Upload database separately (larger files)
echo ""
echo "[2/3] Uploading database..."
rsync -avz -e "ssh -p $RUNPOD_PORT" --progress \
    /home/owner/nz_legal_rag/chroma_db/ \
    root@$RUNPOD_IP:/workspace/nz_legal_rag/chroma_db/

# Upload tenant data
echo ""
echo "[3/3] Uploading tenant data..."
rsync -avz -e "ssh -p $RUNPOD_PORT" --progress \
    /home/owner/nz_legal_rag/tenant_data/ \
    root@$RUNPOD_IP:/workspace/nz_legal_rag/tenant_data/

echo ""
echo "══════════════════════════════════════════════════"
echo "  ✓ Upload Complete!"
echo "══════════════════════════════════════════════════"
echo ""
echo "STORAGE CHECK:"
echo "  ./check_storage.sh $RUNPOD_IP"
echo ""
echo "To start the service:"
echo "  ssh root@$RUNPOD_IP -p $RUNPOD_PORT"
echo "  /workspace/start_legal_advisor.sh"
echo ""
echo "To forward ports locally:"
echo "  ./connect_runpod.sh $RUNPOD_ADDR"
echo ""
echo "⚠️  BACKUP REMINDER:"
echo "  ./backup_runpod.sh $RUNPOD_ADDR"
echo ""
