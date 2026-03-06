#!/bin/bash
# NZ Legal Advisor - RunPod Restore Script
# Restores database backup to RunPod
# Usage: ./restore_runpod.sh <runpod-ip>[:port] <backup-path>

set -e

RUNPOD_ADDR="$1"
BACKUP_PATH="$2"

if [ -z "$RUNPOD_ADDR" ] || [ -z "$BACKUP_PATH" ]; then
    echo "Usage: ./restore_runpod.sh <runpod-ip>[:port] <backup-path>"
    echo "Examples:"
    echo "  ./restore_runpod.sh 194.36.144.12 /home/owner/nz_legal_rag/backups/latest"
    echo "  ./restore_runpod.sh 213.192.2.88:40141 /home/owner/nz_legal_rag/backups/latest"
    exit 1
fi

# Parse IP and port
RUNPOD_IP=$(echo "$RUNPOD_ADDR" | cut -d: -f1)
RUNPOD_PORT=$(echo "$RUNPOD_ADDR" | grep -o ':[0-9]*$' | tr -d ':')

# Default to port 22 if not specified
if [ -z "$RUNPOD_PORT" ]; then
    RUNPOD_PORT=22
fi

if [ ! -d "$BACKUP_PATH" ]; then
    echo "❌ ERROR: Backup path not found: $BACKUP_PATH"
    exit 1
fi

echo "══════════════════════════════════════════════════"
echo "  NZ Legal Advisor - RunPod Restore"
echo "══════════════════════════════════════════════════"
echo ""
echo "Backup Source: $BACKUP_PATH"
echo "Destination: root@$RUNPOD_IP:/workspace/nz_legal_rag/"
echo ""

echo "[1/3] Checking RunPod connectivity..."
if ! ssh -p $RUNPOD_PORT -o ConnectTimeout=5 root@$RUNPOD_IP "echo 'connected'" > /dev/null 2>&1; then
    echo "❌ ERROR: Cannot connect to RunPod at $RUNPOD_IP:$RUNPOD_PORT"
    exit 1
fi
echo "✓ Connected to RunPod"

echo ""
echo "⚠️  WARNING: This will OVERWRITE existing data on RunPod!"
echo ""
read -p "Are you sure you want to continue? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "Restore cancelled."
    exit 0
fi

echo ""
echo "[2/3] Stopping legal advisor service on RunPod..."
ssh -p $RUNPOD_PORT root@$RUNPOD_IP "pkill -f 'python -m api.server' 2>/dev/null || true; pkill -f 'streamlit' 2>/dev/null || true; echo 'Services stopped'" || true
sleep 2

echo ""
echo "[3/3] Restoring backup..."

# Restore chroma_db
if [ -d "$BACKUP_PATH/chroma_db" ]; then
    echo "  → Restoring chroma_db..."
    ssh -p $RUNPOD_PORT root@$RUNPOD_IP "mkdir -p /workspace/nz_legal_rag/chroma_db"
    rsync -avz -e "ssh -p $RUNPOD_PORT" --delete \
        "$BACKUP_PATH/chroma_db/" \
        root@$RUNPOD_IP:/workspace/nz_legal_rag/chroma_db/
    echo "  ✓ chroma_db restored"
else
    echo "  ⚠️  chroma_db not found in backup"
fi

# Restore tenant_data
if [ -d "$BACKUP_PATH/tenant_data" ]; then
    echo "  → Restoring tenant_data..."
    ssh -p $RUNPOD_PORT root@$RUNPOD_IP "mkdir -p /workspace/nz_legal_rag/tenant_data"
    rsync -avz -e "ssh -p $RUNPOD_PORT" --delete \
        "$BACKUP_PATH/tenant_data/" \
        root@$RUNPOD_IP:/workspace/nz_legal_rag/tenant_data/
    echo "  ✓ tenant_data restored"
else
    echo "  ⚠️  tenant_data not found in backup"
fi

echo ""
echo "══════════════════════════════════════════════════"
echo "  ✓ Restore Complete!"
echo "══════════════════════════════════════════════════"
echo ""
echo "To start legal advisor on RunPod:"
echo "  ssh root@$RUNPOD_IP"
echo "  /workspace/start_legal_advisor.sh"
echo ""
