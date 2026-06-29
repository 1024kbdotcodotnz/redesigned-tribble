#!/bin/bash
# NZ Legal Advisor - Daily Sync Script
# Two-way sync between local and RunPod
# Usage: ./sync_daily.sh <runpod-ip>[:port]

set -e

RUNPOD_ADDR="$1"
SYNC_LOG="/home/owner/nz_legal_rag/logs/sync.log"

if [ -z "$RUNPOD_ADDR" ]; then
    echo "Usage: ./sync_daily.sh <runpod-ip>[:port]"
    echo "Examples:"
    echo "  ./sync_daily.sh 194.36.144.12"
    echo "  ./sync_daily.sh 213.192.2.88:40141"
    exit 1
fi

# Parse IP and port
RUNPOD_IP=$(echo "$RUNPOD_ADDR" | cut -d: -f1)
RUNPOD_PORT=$(echo "$RUNPOD_ADDR" | grep -o ':[0-9]*$' | tr -d ':')

# Default to port 22 if not specified
if [ -z "$RUNPOD_PORT" ]; then
    RUNPOD_PORT=22
fi

# Create logs directory
mkdir -p /home/owner/nz_legal_rag/logs

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$SYNC_LOG"
}

echo "══════════════════════════════════════════════════"
echo "  NZ Legal Advisor - Daily Sync"
echo "══════════════════════════════════════════════════"
log "Starting daily sync with RunPod: $RUNPOD_IP"
echo ""

# Check RunPod connectivity
if ! ssh -o ConnectTimeout=5 root@$RUNPOD_IP "echo 'connected'" > /dev/null 2>&1; then
    log "❌ ERROR: Cannot connect to RunPod at $RUNPOD_IP"
    echo "Make sure the pod is running."
    exit 1
fi

echo "Sync Mode: Two-way (local ↔ RunPod)"
echo "Log File: $SYNC_LOG"
echo ""

# ========== SYNC 1: Local → RunPod (Code Updates) ==========
echo "[1/3] Syncing local code changes → RunPod..."
log "Syncing code to RunPod..."

rsync -avz -e "ssh -p $RUNPOD_PORT" --update \
    --exclude=venv \
    --exclude=__pycache__ \
    --exclude='*.pyc' \
    --exclude='*.log' \
    --exclude='backups/' \
    --exclude='logs/sync.log' \
    /home/owner/nz_legal_rag/ \
    root@$RUNPOD_IP:/workspace/nz_legal_rag/ 2>&1 | tee -a "$SYNC_LOG" | tail -5

echo "✓ Code synced to RunPod"
log "Code sync complete"

# ========== SYNC 2: RunPod → Local (Database Updates) ==========
echo ""
echo "[2/3] Syncing database updates ← RunPod..."
log "Syncing database from RunPod..."

# Backup first
BACKUP_DIR="/home/owner/nz_legal_rag/backups/auto_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
if [ -d "/home/owner/nz_legal_rag/chroma_db" ]; then
    cp -r /home/owner/nz_legal_rag/chroma_db "$BACKUP_DIR/" 2>/dev/null || true
fi

echo "  → Auto-backup created: $BACKUP_DIR"

# Sync from RunPod
rsync -avz -e "ssh -p $RUNPOD_PORT" --update \
    root@$RUNPOD_IP:/workspace/nz_legal_rag/chroma_db/ \
    /home/owner/nz_legal_rag/chroma_db/ 2>&1 | tee -a "$SYNC_LOG" | tail -5

# Sync tenant data
rsync -avz -e "ssh -p $RUNPOD_PORT" --update \
    root@$RUNPOD_IP:/workspace/nz_legal_rag/tenant_data/ \
    /home/owner/nz_legal_rag/tenant_data/ 2>&1 | tee -a "$SYNC_LOG" | tail -5

echo "✓ Database synced from RunPod"
log "Database sync complete"

# ========== SYNC 3: Log Files ==========
echo ""
echo "[3/3] Syncing logs..."
rsync -avz -e "ssh -p $RUNPOD_PORT" --update \
    root@$RUNPOD_IP:/workspace/nz_legal_rag/logs/ \
    /home/owner/nz_legal_rag/logs/ 2>/dev/null | tail -3 || echo "  (No new logs)"

echo "✓ Logs synced"

echo ""
echo "══════════════════════════════════════════════════"
echo "  ✓ Daily Sync Complete!"
echo "══════════════════════════════════════════════════"
echo ""
echo "Summary:"
echo "  - Local code → RunPod (updates)"
echo "  - RunPod database → Local (backup)"
echo "  - Logs synced"
echo ""
echo "Last 5 log entries:"
tail -5 "$SYNC_LOG"
echo ""

log "Daily sync complete"
