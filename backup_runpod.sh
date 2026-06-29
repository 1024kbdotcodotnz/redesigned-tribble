#!/bin/bash
# NZ Legal Advisor - RunPod Backup Script
# Backs up database from RunPod to local machine
# Usage: ./backup_runpod.sh <runpod-ip>[:port] [backup-dir]

set -e

RUNPOD_ADDR="$1"
BACKUP_DIR="${2:-/home/owner/nz_legal_rag/backups}"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="legal_advisor_backup_${DATE}"

if [ -z "$RUNPOD_ADDR" ]; then
    echo "Usage: ./backup_runpod.sh <runpod-ip>[:port] [backup-dir]"
    echo "Examples:"
    echo "  ./backup_runpod.sh 194.36.144.12"
    echo "  ./backup_runpod.sh 213.192.2.88:40141"
    exit 1
fi

# Parse IP and port
RUNPOD_IP=$(echo "$RUNPOD_ADDR" | cut -d: -f1)
RUNPOD_PORT=$(echo "$RUNPOD_ADDR" | grep -o ':[0-9]*$' | tr -d ':')

# Default to port 22 if not specified
if [ -z "$RUNPOD_PORT" ]; then
    RUNPOD_PORT=22
fi

echo "══════════════════════════════════════════════════"
echo "  NZ Legal Advisor - RunPod Backup"
echo "══════════════════════════════════════════════════"
echo ""
echo "Source: root@$RUNPOD_IP:$RUNPOD_PORT:/workspace/nz_legal_rag/"
echo "Destination: $BACKUP_DIR/"
echo "Backup Name: $BACKUP_NAME"
echo ""

# Create backup directory
mkdir -p "$BACKUP_DIR"
mkdir -p "$BACKUP_DIR/$BACKUP_NAME"

echo "[1/4] Checking RunPod connectivity..."
if ! ssh -p $RUNPOD_PORT -o ConnectTimeout=5 root@$RUNPOD_IP "echo 'connected'" > /dev/null 2>&1; then
    echo "❌ ERROR: Cannot connect to RunPod at $RUNPOD_IP:$RUNPOD_PORT"
    echo "   Make sure the pod is running and you have SSH access."
    exit 1
fi
echo "✓ Connected to RunPod"

echo ""
echo "[2/4] Backing up database (chroma_db)..."
rsync -avz -e "ssh -p $RUNPOD_PORT" --progress \
    root@$RUNPOD_IP:/workspace/nz_legal_rag/chroma_db/ \
    "$BACKUP_DIR/$BACKUP_NAME/chroma_db/" || {
    echo "⚠️  Warning: chroma_db backup had issues"
}

echo ""
echo "[3/4] Backing up tenant data (API keys, users)..."
rsync -avz -e "ssh -p $RUNPOD_PORT" --progress \
    root@$RUNPOD_IP:/workspace/nz_legal_rag/tenant_data/ \
    "$BACKUP_DIR/$BACKUP_NAME/tenant_data/" || {
    echo "⚠️  Warning: tenant_data backup had issues"
}

echo ""
echo "[4/4] Creating backup manifest..."
cat > "$BACKUP_DIR/$BACKUP_NAME/backup_info.txt" << EOF
NZ Legal Advisor Backup
=======================
Backup Date: $(date)
RunPod IP: $RUNPOD_IP
Source: /workspace/nz_legal_rag/
Destination: $BACKUP_DIR/$BACKUP_NAME/

Contents:
- chroma_db/ (Vector database with $([ -d "$BACKUP_DIR/$BACKUP_NAME/chroma_db" ] && find "$BACKUP_DIR/$BACKUP_NAME/chroma_db" -type f | wc -l) files)
- tenant_data/ (User accounts and API keys)

To restore:
1. Upload to RunPod:
   rsync -avz $BACKUP_DIR/$BACKUP_NAME/chroma_db/ root@<new-pod-ip>:/workspace/nz_legal_rag/chroma_db/
   rsync -avz $BACKUP_DIR/$BACKUP_NAME/tenant_data/ root@<new-pod-ip>:/workspace/nz_legal_rag/tenant_data/

2. Restart legal advisor:
   /workspace/start_legal_advisor.sh
EOF

# Create symlink to latest backup
ln -sfn "$BACKUP_NAME" "$BACKUP_DIR/latest"

# Calculate backup size
BACKUP_SIZE=$(du -sh "$BACKUP_DIR/$BACKUP_NAME" | cut -f1)

echo ""
echo "══════════════════════════════════════════════════"
echo "  ✓ Backup Complete!"
echo "══════════════════════════════════════════════════"
echo ""
echo "Backup Location: $BACKUP_DIR/$BACKUP_NAME/"
echo "Backup Size: $BACKUP_SIZE"
echo "Latest Link: $BACKUP_DIR/latest/"
echo ""
echo "Files backed up:"
echo "  - chroma_db/ (database)"
echo "  - tenant_data/ (users & API keys)"
echo ""
echo "To restore this backup to a new RunPod:"
echo "  ./restore_runpod.sh <new-pod-ip> $BACKUP_DIR/$BACKUP_NAME"
echo ""

# Cleanup old backups (keep last 10)
echo "[Cleanup] Removing backups older than 10 most recent..."
cd "$BACKUP_DIR" && ls -t | grep "legal_advisor_backup_" | tail -n +11 | xargs -r rm -rf
echo "✓ Retained 10 most recent backups"
echo ""
