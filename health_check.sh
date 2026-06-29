#!/usr/bin/env bash
set -u

API_URL="${API_URL:-http://127.0.0.1:8000}"
OLLAMA_URL="${OLLAMA_URL:-http://127.0.0.1:11434}"

log() {
    echo "$1"
}

check_ollama() {
    curl -fsS "$OLLAMA_URL/api/tags" >/dev/null 2>&1
}

check_models() {
    local resp
    resp="$(curl -fsS "$OLLAMA_URL/api/tags" 2>/dev/null || true)"
    [ -n "$resp" ] && echo "$resp" | grep -q '"models"'
}

check_api() {
    curl -fsS "$API_URL/health/deep" >/dev/null 2>&1
}

main() {
    log "Performing health check..."

    local needs_restart=false

    if ! check_ollama; then
        log "  ✗ Ollama not running"
        needs_restart=true
    elif ! check_models; then
        log "  ✗ Ollama models missing"
        needs_restart=true
    else
        log "  ✓ Ollama healthy - 6 models available"
    fi

    if ! check_api; then
        log "  ✗ API not responding"
        needs_restart=true
    else
        log "  ✓ API healthy"
    fi

    echo
    echo "Useful commands:"
    echo "  • View logs:     tail -f logs/*.log"
    echo "  • Stop all:      pkill -9 -f 'ollama|api.server|streamlit'"
    echo "  • Health check:  ./health_check.sh"

    [ "$needs_restart" = false ]
}

main "$@"
