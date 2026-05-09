#!/bin/bash
# Setup automatic daily sync via cron
# Usage: ./setup_cron.sh <runpod-ip>[:port]

RUNPOD_ADDR="$1"

if [ -z "$RUNPOD_ADDR" ]; then
    echo "Usage: ./setup_cron.sh <runpod-ip>[:port]"
    echo "Examples:"
    echo "  ./setup_cron.sh 194.36.144.12"
    echo "  ./setup_cron.sh 213.192.2.88:40141"
    exit 1
fi

RUNPOD_IP=$(echo "$RUNPOD_ADDR" | cut -d: -f1)

SCRIPT_PATH="/home/owner/nz_legal_rag/sync_daily.sh"
CRON_TIME="0 2 * * *"  # 2:00 AM daily

echo "══════════════════════════════════════════════════"
echo "  Setup Automatic Daily Sync"
echo "══════════════════════════════════════════════════"
echo ""
echo "This will set up a daily sync at 2:00 AM"
echo "RunPod: $RUNPOD_ADDR"
echo ""

# Remove existing cron entries for this script
crontab -l 2>/dev/null | grep -v "sync_daily.sh" > /tmp/crontab.tmp || true

# Add new cron job
echo "$CRON_TIME $SCRIPT_PATH $RUNPOD_ADDR >> /home/owner/nz_legal_rag/logs/cron.log 2>&1" >> /tmp/crontab.tmp
crontab /tmp/crontab.tmp
rm /tmp/crontab.tmp

echo "✓ Cron job added"
echo ""
echo "Current cron jobs:"
crontab -l | grep -E "(nz_legal_rag|#)" || echo "  (none)"
echo ""
echo "Daily sync will run at: 2:00 AM"
echo "Logs: /home/owner/nz_legal_rag/logs/cron.log"
echo ""
echo "To remove automatic sync:"
echo "  crontab -e"
echo "  (delete the line with sync_daily.sh)"
echo ""
