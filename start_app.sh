# 1. Clone repo
cd /root
git clone https://1024kbdotcodotnz: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@github.com/1024kbdotcodotnz/redesigned-tribble.git nz_legal_rag

# 2. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama serve &
ollama pull deepseek-r1:14b

# 3. Setup Python environment
export PATH="$HOME/.local/bin:$PATH"
curl -LsSf https://astral.sh/uv/install.sh | sh
cd nz_legal_rag
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt

# 4. Run on port 5801 (the exposed port)
cd web
streamlit run streamlit_app.py --server.port 5801 --server.address 0.0.0.0
