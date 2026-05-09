#!/usr/bin/env python3
"""
NZ Legal RAG - Setup Script
Builds the comprehensive legal database
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from datetime import datetime

def print_header(text):
    """Print formatted header"""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70 + "\n")

def check_ollama():
    """Check if Ollama is installed and running"""
    print("Checking Ollama...")
    
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print("✓ Ollama is installed")
            print(f"\nAvailable models:\n{result.stdout}")
            return True
        else:
            print("✗ Ollama not responding correctly")
            return False
            
    except FileNotFoundError:
        print("✗ Ollama not found. Please install from https://ollama.ai")
        return False
    except subprocess.TimeoutExpired:
        print("✗ Ollama timed out")
        return False

def pull_models():
    """Pull required Ollama models"""
    print_header("Pulling Required Models")
    
    models = [
        ("nomic-embed-text:latest", "Embedding model"),
        ("mixtral:latest", "Primary LLM (large, best quality)"),
        ("llama3.1:latest", "Alternative LLM (faster)"),
        ("mistral:latest", "Alternative LLM (balanced)")
    ]
    
    for model, description in models:
        print(f"\nPulling {model} ({description})...")
        print("This may take several minutes depending on your connection.")
        
        result = subprocess.run(
            ["ollama", "pull", model],
            capture_output=False
        )
        
        if result.returncode == 0:
            print(f"✓ {model} ready")
        else:
            print(f"✗ Failed to pull {model}")

def setup_directories():
    """Create required directory structure"""
    print_header("Setting up Directory Structure")
    
    dirs = [
        "./data/legislation",
        "./data/case_law",
        "./data/police_manual",
        "./data/court_rules",
        "./chroma_db",
        "./secure_data",
        "./tenant_data",
        "./logs"
    ]
    
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"✓ {dir_path}")
    
    print("\nDirectory structure created.")

def install_dependencies():
    """Install Python dependencies"""
    print_header("Installing Dependencies")
    
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
        capture_output=False
    )
    
    if result.returncode == 0:
        print("✓ Dependencies installed")
    else:
        print("✗ Failed to install dependencies")
        sys.exit(1)

def create_env_file():
    """Create .env file with default configuration"""
    print_header("Creating Configuration")
    
    env_content = """# NZ Legal RAG Configuration

# Database paths
CHROMA_DB_PATH=./chroma_db
TENANT_DATA_PATH=./tenant_data

# Ollama configuration
OLLAMA_HOST=http://localhost:11434
EMBEDDING_MODEL=nomic-embed-text
LLM_MODEL=mixtral:latest

# API Server configuration
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=false

# Security
# Generate a strong admin key: openssl rand -hex 32
ADMIN_API_KEY=change-this-in-production

# Data paths
LEGISLATION_DATA_PATH=./data/legislation
CASE_LAW_DATA_PATH=./data/case_law
POLICE_MANUAL_PATH=./data/police_manual

# Feature flags
ENABLE_CONFIDENTIAL_DOCS=true
ENABLE_API=true

# Logging
LOG_LEVEL=INFO
LOG_FILE=./logs/nz_legal_rag.log
"""
    
    env_path = Path(".env")
    if not env_path.exists():
        with open(env_path, "w") as f:
            f.write(env_content)
        print("✓ Created .env file")
        print("  Please review and customize the configuration")
    else:
        print("✓ .env file already exists")

def ingest_legislation():
    """Ingest NZ legislation"""
    print_header("Ingesting NZ Legislation")
    
    from ingestion.nzleg_scraper import NZLegislationScraper
    
    scraper = NZLegislationScraper()
    
    # Download priority Acts
    results = scraper.download_priority_acts()
    print(f"\nDownloaded {results['downloaded']} Acts")
    
    # Create index
    scraper.create_section_index()

def ingest_case_law():
    """Ingest NZ case law"""
    print_header("Ingesting NZ Case Law")
    
    print("""
Note: NZLII scraping should be done respecting their terms of service.
For production use, consider:
1. Using the NZLII bulk data (if available)
2. Partnering with legal publishers
3. Manual curation of key cases

For now, we'll create a structure for manual case addition.
    """)
    
    # Create directory structure
    Path("./data/case_law/by_court/NZSC").mkdir(parents=True, exist_ok=True)
    Path("./data/case_law/by_court/NZCA").mkdir(parents=True, exist_ok=True)
    Path("./data/case_law/by_court/NZHC").mkdir(parents=True, exist_ok=True)
    
    print("✓ Case law directory structure created")
    print("  Add case JSON files to ./data/case_law/by_court/[COURT]/")

def create_sample_data():
    """Create sample data for testing"""
    print_header("Creating Sample Data")
    
    # Sample legislation summary
    sample_leg = {
        "title": "Sample Act Summary",
        "sections": [
            {
                "number": "s 1",
                "title": "Short Title",
                "content": "This Act may be cited as the Sample Act 2024."
            },
            {
                "number": "s 2",
                "title": "Purpose",
                "content": "The purpose of this Act is to demonstrate the database structure."
            }
        ]
    }
    
    with open("./data/legislation/sample_act.json", "w") as f:
        json.dump(sample_leg, f, indent=2)
    
    print("✓ Sample legislation created")
    
    # Sample case
    sample_case = {
        "title": "Sample Case for Testing",
        "citation": "[2024] NZSC 1",
        "court": "NZSC",
        "year": 2024,
        "date": "1 January 2024",
        "judges": ["Sample J"],
        "subjects": ["Sample topic"],
        "headnotes": ["This is a sample case for testing the system."],
        "held_sections": [],
        "full_text": "This case demonstrates the expected format for case law entries.",
        "downloaded_at": datetime.now().isoformat()
    }
    
    with open("./data/case_law/by_court/NZSC/sample_case.json", "w") as f:
        json.dump(sample_case, f, indent=2)
    
    print("✓ Sample case created")

def create_startup_script():
    """Create startup scripts"""
    print_header("Creating Startup Scripts")
    
    # Bash script
    bash_script = """#!/bin/bash
# NZ Legal RAG Startup Script

cd "$(dirname "$0")"

# Load environment
if [ -f .env ]; then
    export $(cat .env | xargs)
fi

# Check Ollama
if ! pgrep -x "ollama" > /dev/null; then
    echo "Starting Ollama..."
    ollama serve &
    sleep 5
fi

echo "Starting NZ Legal RAG..."

# Start API server
echo "Starting API server on port ${API_PORT:-8000}..."
python -m api.server &
API_PID=$!

# Start web interface
echo "Starting web interface on port 8501..."
streamlit run web/streamlit_app.py &
WEB_PID=$!

echo ""
echo "NZ Legal RAG is running!"
echo "  API: http://localhost:${API_PORT:-8000}"
echo "  Web: http://localhost:8501"
echo ""
echo "Press Ctrl+C to stop"

# Wait for interrupt
trap "kill $API_PID $WEB_PID; exit" INT
wait
"""
    
    with open("start.sh", "w") as f:
        f.write(bash_script)
    
    os.chmod("start.sh", 0o755)
    print("✓ Created start.sh")
    
    # Windows batch script
    batch_script = """@echo off
REM NZ Legal RAG Startup Script (Windows)

cd /d "%~dp0"

REM Load environment
if exist .env (
    for /f "tokens=*" %%a in (.env) do set %%a
)

echo Starting NZ Legal RAG...

REM Start API server
echo Starting API server...
start python -m api.server

REM Start web interface
echo Starting web interface...
start streamlit run web/streamlit_app.py

echo.
echo NZ Legal RAG is running!
echo   API: http://localhost:8000
echo   Web: http://localhost:8501
echo.
pause
"""
    
    with open("start.bat", "w") as f:
        f.write(batch_script)
    
    print("✓ Created start.bat")

def create_readme():
    """Create comprehensive README"""
    readme = """# NZ Legal RAG

A comprehensive New Zealand legal information reference database with RAG (Retrieval-Augmented Generation) capabilities.

## Features

- **Comprehensive Legal Database**: NZ Legislation, Case Law, Police Manual
- **AI-Powered Analysis**: Using local Ollama LLMs for privacy
- **Secure Document Processing**: Confidential document handling with PII redaction
- **Multi-Tenant Access**: Community, Professional, and Enterprise tiers
- **Similarity Matching**: Find cases with similar fact patterns
- **Element Checking**: Verify legal elements against facts

## Quick Start

### 1. Prerequisites

- Python 3.10+
- Ollama (https://ollama.ai)
- 16GB+ RAM recommended
- 50GB+ free disk space

### 2. Installation

```bash
# Clone the repository
git clone <repository-url>
cd nz_legal_rag

# Run setup
python setup.py
```

### 3. Configuration

Edit `.env` file to customize settings:

```bash
# Required: Set your admin API key
ADMIN_API_KEY=your-secure-random-key-here

# Optional: Customize paths and models
CHROMA_DB_PATH=./chroma_db
LLM_MODEL=mixtral:latest
```

### 4. Start the System

```bash
# Linux/Mac
./start.sh

# Windows
start.bat
```

Access:
- Web Interface: http://localhost:8501
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Usage

### Web Interface

1. Open http://localhost:8501
2. Enter your API key (create one with `python -m security.tenant_manager create`)
3. Use the search, analysis, and case matching features

### API

```python
import requests

# Search
response = requests.post("http://localhost:8000/api/v1/search", 
    headers={"Authorization": "Bearer YOUR_API_KEY"},
    json={"query": "search warrant section 21 BORA"}
)

# Legal analysis
response = requests.post("http://localhost:8000/api/v1/analyze",
    headers={"Authorization": "Bearer YOUR_API_KEY"},
    json={
        "query": "Evaluate the validity of this search warrant...",
        "analysis_type": "search_warrant"
    }
)
```

### CLI

```bash
# Search
python -m core.rag_engine -q "possession for supply elements"

# Create tenant
python -m security.tenant_manager create -n "Law Firm ABC" -t professional

# Scrape legislation
python -m ingestion.nzleg_scraper
```

## Directory Structure

```
nz_legal_rag/
├── api/                    # FastAPI REST API
├── core/                   # Core RAG engine
├── ingestion/              # Data ingestion scripts
├── security/               # Authentication & encryption
├── web/                    # Streamlit web interface
├── data/                   # Downloaded legal data
│   ├── legislation/        # NZ Acts and Regulations
│   ├── case_law/          # NZLII cases
│   └── police_manual/     # Police Manual chapters
├── chroma_db/             # Vector database
├── secure_data/           # Encrypted confidential docs
└── tenant_data/           # Tenant configurations
```

## Data Sources

- **Legislation**: legislation.govt.nz (CC BY 4.0)
- **Case Law**: nzlii.org (CC BY-SA 4.0)
- **Police Manual**: police.govt.nz (Crown Copyright)

## Security

- All confidential documents are encrypted at rest
- Local LLM processing - no data leaves your machine
- PII detection and redaction
- Multi-tenant isolation
- Audit logging

## License

This project is provided for legal research and educational purposes. 
Users are responsible for complying with data source licenses and 
applicable laws.

## Support

For issues and feature requests, please use the issue tracker.

## Acknowledgments

- New Zealand Legislation website
- New Zealand Legal Information Institute (NZLII)
- New Zealand Police
- Ollama project
- ChromaDB project
"""
    
    with open("README.md", "w") as f:
        f.write(readme)
    
    print("✓ Created README.md")

def main():
    """Main setup process"""
    print("""
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║              NZ Legal RAG - Setup Script                         ║
║                                                                  ║
║   New Zealand Legal Research Database with AI-Powered RAG       ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
    """)
    
    # Check Python version
    if sys.version_info < (3, 10):
        print("Error: Python 3.10 or higher required")
        sys.exit(1)
    
    print(f"Python version: {sys.version}")
    
    # Install dependencies first
    install_dependencies()
    
    # Check Ollama
    if not check_ollama():
        print("\nPlease install Ollama first: https://ollama.ai")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)
    else:
        pull_models()
    
    # Setup directories
    setup_directories()
    
    # Create configuration
    create_env_file()
    
    # Create sample data
    create_sample_data()
    
    # Create startup scripts
    create_startup_script()
    
    # Create documentation
    create_readme()
    
    print_header("Setup Complete!")
    
    print("""
Next steps:

1. Review and customize the .env configuration file

2. Create your first tenant:
   python -m security.tenant_manager create -n "Your Name" -t professional

3. Start the system:
   ./start.sh (Linux/Mac) or start.bat (Windows)

4. Access the web interface at http://localhost:8501

5. For data ingestion:
   python -m ingestion.nzleg_scraper
   python -m ingestion.police_manual_scraper

For help, see README.md
    """)

if __name__ == "__main__":
    main()
