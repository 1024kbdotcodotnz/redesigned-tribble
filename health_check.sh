#!/bin/bash
# Health Check and Auto-Recovery Script
# Can be run manually or via cron to ensure services stay up

set -e

cd /workspace/nz_legal_rag

API_URL="http://localhost:8000"
OLLAMA_URL="http://localhost:11434"
LOG_FILE="logs/health_check.log"

mkdir -p logs
touch "$LOG_FILE"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

check_api() {
    if curl -s "$API_URL/health" > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

check_ollama() {
    if curl -s "$OLLAMA_URL/api/tags" > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

check_models() {
    local models=$(curl -s "$OLLAMA_URL/api/tags" 2>/dev/null | grep -o '"name":"[^"]*"' | wc -l)
    if [ "$models" -ge 2 ]; then
        return 0
    else
        return 1
    fi
}

main() {
    log "Starting health check..."
    
    local needs_restart=false
    
    # Check Ollama
    if ! check_ollama; then
        log "⚠ Ollama not running, will restart services"
        needs_restart=true
    elif ! check_models; then
        log "⚠ Ollama models missing, will run auto-recovery"
        needs_restart=true
    else
        log "✓ Ollama is healthy"
    fi
    
    # Check API
    if ! check_api; then
        log "⚠ API not responding, will restart services"
        needs_restart=true
    else
        log "✓ API is healthy"
    fi
    
    # Restart if needed
    if [ "$needs_restart" = true ]; then
        log "🔄 Restarting services with auto-recovery..."
        ./start_with_recovery.sh > logs/restart.log 2>&1
        log "✓ Services restarted"
        
        # Verify
        sleep 5
        if check_api && check_ollama && check_models; then
            log "✓ Health check passed after restart"
        else
            log "✗ Health check failed after restart - manual intervention needed"
        fi
    else
        log "✓ All services healthy"
    fi
}

main "$@"
