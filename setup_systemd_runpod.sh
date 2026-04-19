#!/bin/bash
# Install systemd services for NZ Legal RAG on RunPod
# Run as root on the RunPod instance

set -e

APP_DIR="/workspace/nz_legal_rag"
VENV_PYTHON="$APP_DIR/.venv/bin/python"
VENV_STREAMLIT="$APP_DIR/.venv/bin/streamlit"

echo "Installing NZ Legal RAG systemd services..."

# API Service
cat > /etc/systemd/system/nzlegal-api.service <<EOF
[Unit]
Description=NZ Legal RAG API Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$APP_DIR
Environment=OLLAMA_URL=http://localhost:11434
Environment=CHROMA_DB_PATH=./chroma_db
Environment=TENANT_DATA_PATH=./tenant_data
Environment=API_HOST=0.0.0.0
Environment=API_PORT=8000
Environment=LLM_MODEL=deepseek-r1:14b
Environment=EMBEDDING_MODEL=nomic-embed-text:latest
ExecStart=$VENV_PYTHON -m api.server
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Streamlit Service
cat > /etc/systemd/system/nzlegal-web.service <<EOF
[Unit]
Description=NZ Legal RAG Web UI
After=network.target nzlegal-api.service

[Service]
Type=simple
User=root
WorkingDirectory=$APP_DIR
Environment=API_URL=http://localhost:8000
ExecStart=$VENV_STREAMLIT run web/streamlit_app.py --server.port=5801 --server.address=0.0.0.0 --server.headless=true
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# MCP Service
cat > /etc/systemd/system/nzlegal-mcp.service <<EOF
[Unit]
Description=NZ Legal RAG MCP Server
After=network.target nzlegal-api.service

[Service]
Type=simple
User=root
WorkingDirectory=$APP_DIR
Environment=OLLAMA_URL=http://localhost:11434
Environment=CHROMA_DB_PATH=./chroma_db
Environment=MCP_TRANSPORT=streamable-http
Environment=MCP_HOST=0.0.0.0
Environment=MCP_PORT=8080
Environment=MCP_PATH=/mcp
Environment=LLM_MODEL=deepseek-r1:14b
Environment=EMBEDDING_MODEL=nomic-embed-text:latest
ExecStart=$VENV_PYTHON -m api.mcp_server --transport streamable-http --host 0.0.0.0 --port 8080 --path /mcp --stateless
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Reload and enable
systemctl daemon-reload
systemctl enable nzlegal-api.service nzlegal-web.service nzlegal-mcp.service

echo "✓ Services installed and enabled"
echo ""
echo "Start them now:"
echo "  systemctl start nzlegal-api nzlegal-web nzlegal-mcp"
echo ""
echo "Check status:"
echo "  systemctl status nzlegal-api"
echo "  systemctl status nzlegal-web"
echo "  systemctl status nzlegal-mcp"
echo ""
echo "View logs:"
echo "  journalctl -u nzlegal-api -f"
echo "  journalctl -u nzlegal-mcp -f"
