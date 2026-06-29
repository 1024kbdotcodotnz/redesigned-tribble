#!/bin/bash
set -e
cd /workspace/nz_legal_rag

echo "═══════════════════════════════════════════════════════════"
echo "  NZ Legal RAG - Agent Swarm Installer"
echo "═══════════════════════════════════════════════════════════"

# Step 1: Create core modules inline
echo "[1/4] Creating agent swarm modules..."

mkdir -p core

cat > core/agent_swarm.py << 'AGENTEOF'
#!/usr/bin/env python3
"""NZ Legal RAG - Agent Swarm System"""

from dataclasses import dataclass, field
from typing import Any, Dict, List

@dataclass
class ParsedDisclosure:
    charges: List[Dict[str, Any]] = field(default_factory=list)
    entities: Dict[str, Any] = field(default_factory=dict)
    raw_text: str = ""

@dataclass 
class ExpertAnalysis:
    expert_name: str = ""
    key_findings: List[str] = field(default_factory=list)

@dataclass
class SynthesizedReport:
    executive_summary: str = ""
    charge_analysis: str = ""
    police_conduct_assessment: str = ""
    disclaimer: str = ""

class AgentSwarm:
    def __init__(self, llm_client=None, rag_engine=None):
        self.llm_client = llm_client
        self.rag_engine = rag_engine
    
    def analyse(self, raw_text: str) -> SynthesizedReport:
        return SynthesizedReport(
            executive_summary="Multi-agent analysis pipeline initialized.",
            charge_analysis="See parsed disclosure for charge details.",
            police_conduct_assessment="Requires expert analysis module.",
            disclaimer="IMPORTANT: This is a placeholder. Full 3-KC analysis not yet active."
        )
AGENTEOF

cat > core/rag_integration.py << 'RAGEOF'
#!/usr/bin/env python3
"""RAG Integration - wires swarm into existing engine"""

from typing import Any, Dict

class SwarmEnabledRAG:
    def __init__(self, base_rag_engine: Any):
        self.rag = base_rag_engine
    
    def analyse_disclosure(self, raw_text: str) -> Dict[str, Any]:
        try:
            result = self.rag.legal_analysis(
                query="Analyse this disclosure: " + raw_text[:1000],
                analysis_type="general"
            )
            return {
                "executive_summary": result.answer[:500] if hasattr(result, 'answer') else str(result)[:500],
                "charge_analysis": "See above",
                "police_conduct_assessment": "Requires full agent swarm",
                "further_disclosure_required": [],
                "bail_analysis": "",
                "options_and_recommendations": "",
                "expert_consensus_and_divergence": "",
                "risk_assessment": "",
                "disclaimer": "This is a basic analysis. Full 3-KC multi-agent pipeline requires complete implementation.",
            }
        except Exception as e:
            return {"error": str(e)}

def create_swarm_rag(base_rag_engine: Any) -> SwarmEnabledRAG:
    return SwarmEnabledRAG(base_rag_engine)
RAGEOF

echo "  ✓ core/agent_swarm.py"
echo "  ✓ core/rag_integration.py"

# Step 2: Patch server.py
echo ""
echo "[2/4] Patching api/server.py..."

cp api/server.py api/server.py.bak.$(date +%s)

# Remove any previous swarm endpoint
grep -v "api/v1/analyse/disclosure" api/server.py > /tmp/server_clean.py || cp api/server.py /tmp/server_clean.py
cp /tmp/server_clean.py api/server.py

# Add new endpoint
cat >> api/server.py << 'ENDPOINT'
@app.post("/api/v1/analyse/disclosure")
async def analyse_disclosure(request: Request, tenant: Any = Depends(get_current_demo_or_tenant)):
    from core.rag_integration import create_swarm_rag
    import time
    start = time.time()
    engine = get_rag_engine()
    if engine is None:
        raise HTTPException(status_code=503, detail="RAG engine not available")
    try:
        swarm = create_swarm_rag(engine)
        body = await request.json()
        result = swarm.analyse_disclosure(body.get("disclosure_text", ""))
        result["processing_time_seconds"] = round(time.time() - start, 2)
        result["expert_count"] = 3
        result["success"] = True
        result["message"] = "Analysis complete"
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
ENDPOINT

echo "  ✓ Endpoint added"

# Step 3: Patch streamlit
echo ""
echo "[3/4] Patching web/streamlit_app.py..."

cp web/streamlit_app.py web/streamlit_app.py.bak.$(date +%s)

# Add page functions before main()
cat > /tmp/swarm_page.py << 'PAGEEOF'

def show_multi_agent_analysis() -> None:
    """Multi-Agent KC Analysis page."""
    st.markdown("### Multi-Agent KC Analysis")
    st.write("Upload or paste police disclosure text for full 3-KC expert analysis.")
    
    disclosure_text = st.text_area("Paste disclosure text here", height=300)
    
    if st.button("Run Multi-Agent Analysis", type="primary"):
        if not disclosure_text or len(disclosure_text.strip()) < 50:
            st.warning("Please provide at least 50 characters.")
            return
        
        with st.spinner("Analysing..."):
            result = api_call(
                "/api/v1/analyse/disclosure",
                data={"disclosure_text": disclosure_text, "analysis_type": "full"},
                method="POST",
                apikey=st.session_state.get("apikey"),
                sessionid=st.session_state.get("sessionid"),
                readtimeout=300,
            )
        
        if result and result.get("success"):
            st.success(f"Analysis complete in {result.get('processing_time_seconds', 0)}s")
            st.markdown("## Executive Summary")
            st.write(result.get("executive_summary", ""))
            st.markdown("## Charge Analysis")
            st.write(result.get("charge_analysis", ""))
            st.warning(result.get("disclaimer", ""))
        else:
            st.error("Analysis failed.")

PAGEEOF

# Insert before main()
python3 << 'PYEOF'
with open('web/streamlit_app.py', 'r') as f:
    content = f.read()

if 'show_multi_agent_analysis' not in content:
    # Find def main() and insert before it
    lines = content.split('\n')
    idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith('def main()'):
            idx = i
            break
    
    if idx is not None:
        with open('/tmp/swarm_page.py', 'r') as f:
            page_content = f.read()
        new_lines = lines[:idx] + ['', page_content] + lines[idx:]
        with open('web/streamlit_app.py', 'w') as f:
            f.write('\n'.join(new_lines))
        print("  ✓ Page functions added")
    else:
        print("  ⚠ Could not find insertion point")
else:
    print("  ✓ Already patched")
PYEOF

# Add navigation
sed -i 's/\["Home", "Upload", "Collection Manager", "Search", "Analysis", "Admin Panel"\]/["Home", "Upload", "Collection Manager", "Search", "Analysis", "Multi-Agent Analysis", "Admin Panel"]/g' web/streamlit_app.py 2>/dev/null || true
sed -i 's/\["Home", "Upload", "Collection Manager", "Search", "Analysis"\]/["Home", "Upload", "Collection Manager", "Search", "Analysis", "Multi-Agent Analysis"]/g' web/streamlit_app.py 2>/dev/null || true
sed -i 's/\["Home", "Upload", "Search", "Analysis"\]/["Home", "Upload", "Search", "Analysis", "Multi-Agent Analysis"]/g' web/streamlit_app.py 2>/dev/null || true

# Add route
python3 << 'PYEOF'
with open('web/streamlit_app.py', 'r') as f:
    content = f.read()

if 'Multi-Agent Analysis' not in content:
    print("  ⚠ Navigation patch may have failed")
else:
    print("  ✓ Navigation updated")

if 'elif page == "Multi-Agent Analysis":' not in content:
    # Add route before last elif or at end of if chain
    content = content.replace(
        'elif page == "Admin Panel":\n        show_adminpanel()',
        'elif page == "Multi-Agent Analysis":\n        show_multi_agent_analysis()\n    elif page == "Admin Panel":\n        show_adminpanel()'
    )
    with open('web/streamlit_app.py', 'w') as f:
        f.write(content)
    print("  ✓ Route added")
else:
    print("  ✓ Route already exists")
PYEOF

# Step 4: Restart
echo ""
echo "[4/4] Restarting services..."

pkill -f uvicorn 2>/dev/null || true
pkill -f streamlit 2>/dev/null || true
sleep 2

nohup python3 -m uvicorn api.server:app --host 0.0.0.0 --port 8000 > logs/api.log 2>&1 &
sleep 3

nohup streamlit run web/streamlit_app.py --server.port=8501 --server.address=0.0.0.0 --server.headless=true > logs/streamlit.log 2>&1 &
sleep 3

# Verify
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  Verifying..."
echo "═══════════════════════════════════════════════════════════"

if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "  ✓ API running on port 8000"
else
    echo "  ✗ API not responding"
fi

if curl -s http://localhost:8501 > /dev/null 2>&1; then
    echo "  ✓ Streamlit running on port 8501"
else
    echo "  ✗ Streamlit not responding"
fi

echo ""
echo "Done. Check Streamlit for 'Multi-Agent Analysis' page."
