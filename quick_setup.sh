#!/bin/bash
# Quick Setup Script for NZ Legal RAG

set -e  # Exit on error

echo "═══════════════════════════════════════════════════════════════"
echo "  NZ Legal RAG - Quick Setup"
echo "═══════════════════════════════════════════════════════════════"
echo ""

cd "$(dirname "$0")"

# Step 1: Create directories
echo "📁 Creating directories..."
mkdir -p data/{legislation,case_law,police_manual,court_rules}
mkdir -p chroma_db tenant_data secure_data logs

# Step 2: Setup Python environment
echo ""
echo "🐍 Setting up Python environment..."

if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✓ Created virtual environment"
else
    echo "✓ Virtual environment exists"
fi

# Activate and install
source venv/bin/activate
echo "✓ Activated virtual environment"

# Install requirements
echo ""
echo "📦 Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo "✓ Dependencies installed"

# Step 3: Create .env file
echo ""
echo "⚙️  Creating configuration..."

if [ ! -f ".env" ]; then
    # Generate random admin key
    ADMIN_KEY=$(openssl rand -hex 32 2>/dev/null || cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 64 | head -n 1)
    
    cat > .env << EOF
# NZ Legal RAG Configuration
CHROMA_DB_PATH=./chroma_db
TENANT_DATA_PATH=./tenant_data
OLLAMA_HOST=http://localhost:11434
EMBEDDING_MODEL=nomic-embed-text
LLM_MODEL=mixtral:latest
API_HOST=0.0.0.0
API_PORT=8000
ADMIN_API_KEY=$ADMIN_KEY
ENABLE_CONFIDENTIAL_DOCS=true
ENABLE_API=true
LOG_LEVEL=INFO
LOG_FILE=./logs/nz_legal_rag.log
EOF
    echo "✓ Created .env file"
    echo ""
    echo "⚠️  IMPORTANT: Your admin API key is:"
    echo "   $ADMIN_KEY"
    echo ""
    echo "   Save this key - it will not be shown again!"
else
    echo "✓ .env file already exists"
fi

# Step 4: Check Ollama
echo ""
echo "🔍 Checking Ollama..."

if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "✓ Ollama is running"
    echo ""
    echo "Available models:"
    ollama list | grep -E "(mixtral|nomic-embed-text|mistral|llama)" || true
else
    echo "⚠️  Ollama is not running!"
    echo ""
    echo "Please start Ollama first:"
    echo "   ollama serve"
    echo ""
    exit 1
fi

# Step 5: Check required models
echo ""
echo "🔍 Checking required models..."

if ! ollama list | grep -q "nomic-embed-text"; then
    echo "📥 Pulling nomic-embed-text..."
    ollama pull nomic-embed-text
fi

if ! ollama list | grep -q "mixtral"; then
    echo "📥 Pulling mixtral..."
    ollama pull mixtral:latest
fi

echo "✓ Required models available"

# Step 6: Create first tenant
echo ""
echo "👤 Creating first tenant..."
source venv/bin/activate

python3 << 'PYTHON'
import sys
sys.path.insert(0, '.')
from security.tenant_manager import TenantManager, AccessTier

manager = TenantManager()

# Check if any tenants exist
if not manager.tenants:
    tenant_id, api_key = manager.create_tenant(
        name="Default User",
        tier=AccessTier.PROFESSIONAL,
        days_valid=365
    )
    print(f"\n✓ Created default tenant")
    print(f"  Tenant ID: {tenant_id}")
    print(f"  API Key: {api_key}")
    print(f"\n⚠️  SAVE THIS API KEY - it cannot be retrieved later!")
else:
    print("✓ Tenants already exist")
    print(f"  Existing tenants: {len(manager.tenants)}")
PYTHON

# Step 7: Create sample data
echo ""
echo "📚 Creating sample data..."

# Sample legislation summary
cat > data/legislation/sample_crimes_act.json << 'EOF'
{
  "title": "Crimes Act 1961",
  "act_id": "crimes_act_1961",
  "sections": [
    {
      "number": "s 21",
      "title": "Parties to offences",
      "content": "Every one is a party to and guilty of an offence who: (a) Actually commits the offence; (b) Does or omits an act for the purpose of aiding any person to commit the offence; (c) Abets any person in the commission of the offence; (d) Incites, counsels, or procures any person to commit the offence."
    },
    {
      "number": "s 310",
      "title": "Conspiracy to commit offence",
      "content": "(1) Every one who conspires to commit any offence is liable to imprisonment for a term not exceeding 7 years. (2) If the offence is punishable by life imprisonment, the conspiracy is also punishable by life imprisonment."
    }
  ]
}
EOF

# Sample case law
cat > data/case_law/sample_shaheed.json << 'EOF'
{
  "title": "R v Shaheed",
  "citation": "[2002] 2 NZLR 377",
  "court": "NZCA",
  "year": 2002,
  "date": "",
  "judges": ["Richardson P", "Gault J", "Keith J", "Tipping J", "Anderson J"],
  "subjects": ["evidence", "exclusion", "s 21 BORA", "unreasonable search"],
  "headnotes": ["Established the framework for exclusion of evidence under s 30 Evidence Act 2006"],
  "held_sections": [
    {
      "type": "held",
      "text": "Evidence obtained in breach of s 21 NZBORA is not automatically inadmissible. The court must apply a balancing test weighing the seriousness of the breach against the public interest in admitting the evidence."
    }
  ],
  "full_text": "R v Shaheed [2002] 2 NZLR 377 (CA) - Leading case on exclusion of improperly obtained evidence. Established the balancing test framework that was later codified in s 30 of the Evidence Act 2006.",
  "downloaded_at": ""
}
EOF

echo "✓ Sample data created"

# Step 8: Final instructions
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  ✅ Setup Complete!"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "Next steps:"
echo ""
echo "1. Start the system:"
echo "   ./start.sh"
echo ""
echo "2. Access the services:"
echo "   🌐 Web Interface: http://localhost:8501"
echo "   🔌 API:           http://localhost:8000"
echo "   📚 API Docs:      http://localhost:8000/docs"
echo ""
echo "3. Or use the CLI:"
echo "   source venv/bin/activate"
echo "   python -m core.rag_engine -q 'search warrant requirements'"
echo ""
echo "4. To ingest more data:"
echo "   python -m ingestion.nzleg_scraper"
echo "   python -m ingestion.police_manual_scraper"
echo ""
echo "═══════════════════════════════════════════════════════════════"
