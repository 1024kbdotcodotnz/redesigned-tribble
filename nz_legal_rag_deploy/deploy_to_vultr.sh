#!/bin/bash
set -e

# NZ Legal RAG - Vultr GPU Deployment Script
# Usage: ./deploy_to_vultr.sh <VULTR_IP>

VULTR_IP="${1:-}"
SSH_USER="${2:-root}"
DEPLOY_DIR="/opt/nzlegal"
APP_NAME="nzlegal"

if [ -z "$VULTR_IP" ]; then
    echo "Usage: ./deploy_to_vultr.sh <VULTR_IP> [SSH_USER]"
    echo "Example: ./deploy_to_vultr.sh 203.0.113.45"
    exit 1
fi

echo "═══════════════════════════════════════════════════════════"
echo "  Deploying NZ Legal RAG to Vultr: $VULTR_IP"
echo "═══════════════════════════════════════════════════════════"

# --- Build tarball ---
TARBALL="/tmp/nzlegal-vultr-deploy.tar.gz"
echo ""
echo "📦 Packaging application (including chroma_db contents)..."

# Use -h to dereference the chroma_db symlink so the actual DB is included
tar -chzf "$TARBALL" \
    --exclude='.git' \
    --exclude='.venv' \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='*.pyo' \
    --exclude='.streamlit_app.py.swp' \
    --exclude='.kimi' \
    --exclude='logs/*.log' \
    --exclude='nz_legal_rag_deploy.zip' \
    --exclude='contents.zip' \
    -C "$(dirname "$0")" \
    .

TARBALL_SIZE=$(du -h "$TARBALL" | cut -f1)
echo "✓ Tarball created: $TARBALL ($TARBALL_SIZE)"

# --- Upload ---
echo ""
echo "🚀 Uploading to $SSH_USER@$VULTR_IP:$DEPLOY_DIR ..."
ssh -o StrictHostKeyChecking=accept-new "$SSH_USER@$VULTR_IP" "mkdir -p $DEPLOY_DIR"
scp "$TARBALL" "$SSH_USER@$VULTR_IP:$DEPLOY_DIR/nzlegal-deploy.tar.gz"

# --- Extract & Start ---
echo ""
echo "🔧 Extracting and starting services..."
ssh "$SSH_USER@$VULTR_IP" << EOF
    set -e
    cd $DEPLOY_DIR
    echo "Extracting archive..."
    tar -xzf nzlegal-deploy.tar.gz
    rm -f nzlegal-deploy.tar.gz
    
    echo "Ensuring .env is present..."
    if [ ! -f .env ]; then
        cp .env.example .env
    fi
    
    echo "Setting permissions..."
    chmod -R 755 .
    
    echo "Pulling latest Docker images..."
    docker compose -f docker-compose.vultr.yml pull || true
    
    echo "Building and starting containers..."
    docker compose -f docker-compose.vultr.yml up -d --build
    
    echo "Waiting for API health check..."
    for i in {1..30}; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            echo "✓ API is ready"
            break
        fi
        sleep 2
    done
    
    echo ""
    echo "Deployment complete!"
EOF

# --- Cleanup ---
rm -f "$TARBALL"

# --- Summary ---
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  ✅ DEPLOYMENT COMPLETE"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "  🌐 Web Demo:     http://$VULTR_IP"
echo "  🔌 API Docs:     http://$VULTR_IP:8000/docs"
echo "  📊 Admin Panel:  http://$VULTR_IP (login as admin)"
echo ""
echo "  Demo Accounts:"
echo "    admin / demo-admin-2024!"
echo "    staff / demo-staff-2024!"
echo "    user  / demo-user-2024!"
echo ""
echo "  SSH Management:"
echo "    ssh $SSH_USER@$VULTR_IP"
echo "    sudo docker logs -f nzlegal-api"
echo "    sudo docker logs -f nzlegal-web"
echo ""
echo "═══════════════════════════════════════════════════════════"
