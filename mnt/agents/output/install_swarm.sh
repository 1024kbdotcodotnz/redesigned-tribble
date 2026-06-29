#!/bin/bash
# NZ Legal RAG - Agent Swarm Auto-Installer
# Run this from /workspace/nz_legal_rag to wire everything automatically

set -e

cd /workspace/nz_legal_rag

echo "═══════════════════════════════════════════════════════════"
echo "  NZ Legal RAG - Agent Swarm Auto-Installer"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Check we're in the right place
if [ ! -f "api/server.py" ] || [ ! -d "web" ]; then
    echo "ERROR: Run this from /workspace/nz_legal_rag"
    exit 1
fi

source .venv/bin/activate 2>/dev/null || echo "No venv found, using system Python"

# ─── Step 1: Copy core modules ─────────────────────────────────────────────
echo "[1/6] Copying core agent modules..."

mkdir -p core

# Copy from output directory if available, otherwise from upload
if [ -f "/mnt/agents/output/agent_swarm.py" ]; then
    cp /mnt/agents/output/agent_swarm.py core/agent_swarm.py
    cp /mnt/agents/output/rag_integration.py core/rag_integration.py
elif [ -f "/workspace/agent_swarm.py" ]; then
    cp /workspace/agent_swarm.py core/agent_swarm.py
    cp /workspace/rag_integration.py core/rag_integration.py
else
    echo "ERROR: Cannot find agent_swarm.py or rag_integration.py"
    echo "Please download them first and place in /workspace/"
    exit 1
fi

echo "  ✓ core/agent_swarm.py"
echo "  ✓ core/rag_integration.py"

# ─── Step 2: Backup server.py ──────────────────────────────────────────────
echo ""
echo "[2/6] Patching api/server.py..."
cp api/server.py api/server.py.bak.$(date +%s)

# Add the new endpoint to server.py
# First, check if already patched
if grep -q "/api/v1/analyse/disclosure" api/server.py; then
    echo "  ⚠ Endpoint already exists, skipping"
else
    # Find the line with "class AnalysisResponse" and insert before it
    # Or find a good insertion point (after the last endpoint)

    # Create temporary file with new endpoint
    cat > /tmp/new_endpoint.py << 'ENDPOINT'

# ─── Multi-Agent Analysis Models ────────────────────────────────────────────

class MultiAgentAnalysisRequest(BaseModel):
    disclosure_text: str = Field(..., min_length=50, description="Raw disclosure text to analyse")
    analysis_type: str = Field(default="full", description="Type of analysis: full, quick, or charges_only")
    include_expert_divergence: bool = Field(default=True, description="Include expert divergence analysis")

class MultiAgentAnalysisResponse(BaseModel):
    success: bool
    message: str
    executive_summary: str
    disclosure_overview: str
    charge_analysis: str
    summary_of_facts_review: str
    police_conduct_assessment: str
    further_disclosure_required: list
    bail_analysis: str
    options_and_recommendations: str
    expert_consensus_and_divergence: str
    risk_assessment: str
    disclaimer: str
    processing_time_seconds: float
    expert_count: int

# ─── Multi-Agent Analysis Endpoint ────────────────────────────────────────

@app.post("/api/v1/analyse/disclosure", response_model=MultiAgentAnalysisResponse)
async def analyse_disclosure(
    request: MultiAgentAnalysisRequest,
    tenant: Any = Depends(get_current_demo_or_tenant),
):
    """
    Run full multi-agent KC analysis on disclosure text.
    Activates: Parser, QueryGen, 3×KC Experts, Orchestrator.
    """
    import time
    start_time = time.time()

    check_quota_flexible(tenant, "query")

    engine = get_rag_engine()
    if engine is None:
        raise HTTPException(status_code=503, detail="RAG engine not available")

    try:
        from core.rag_integration import create_swarm_rag
        swarm_rag = create_swarm_rag(engine)
    except ImportError as e:
        raise HTTPException(status_code=503, detail=f"Agent swarm not available: {e}")

    try:
        result = swarm_rag.analyse_disclosure(request.disclosure_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    processing_time = time.time() - start_time

    if tenant_manager is not None:
        tenant_manager.record_usage(
            _get_tenant_id(tenant),
            query_count=1,
            api_calls=1,
        )

    return {
        "success": True,
        "message": "Multi-agent analysis complete",
        "executive_summary": result.get("executive_summary", ""),
        "disclosure_overview": result.get("disclosure_overview", ""),
        "charge_analysis": result.get("charge_analysis", ""),
        "summary_of_facts_review": result.get("summary_of_facts_review", ""),
        "police_conduct_assessment": result.get("police_conduct_assessment", ""),
        "further_disclosure_required": result.get("further_disclosure_required", []),
        "bail_analysis": result.get("bail_analysis", ""),
        "options_and_recommendations": result.get("options_and_recommendations", ""),
        "expert_consensus_and_divergence": result.get("expert_consensus_and_divergence", ""),
        "risk_assessment": result.get("risk_assessment", ""),
        "disclaimer": result.get("disclaimer", ""),
        "processing_time_seconds": round(processing_time, 2),
        "expert_count": 3,
    }

ENDPOINT

    # Insert before the last endpoint or at the end before if __name__
    # Find line with "if __name__" and insert before it
    if grep -q "if __name__" api/server.py; then
        # Get line number of "if __name__"
        LINENO=$(grep -n "if __name__" api/server.py | head -1 | cut -d: -f1)
        # Split file and insert
        head -n $((LINENO - 1)) api/server.py > /tmp/server_top.py
        tail -n +$LINENO api/server.py > /tmp/server_bottom.py
        cat /tmp/server_top.py /tmp/new_endpoint.py /tmp/server_bottom.py > api/server.py
        echo "  ✓ Endpoint added to api/server.py"
    else
        # Just append to end
        cat /tmp/new_endpoint.py >> api/server.py
        echo "  ✓ Endpoint appended to api/server.py"
    fi
fi

# ─── Step 3: Patch Streamlit app ─────────────────────────────────────────
echo ""
echo "[3/6] Patching web/streamlit_app.py..."
cp web/streamlit_app.py web/streamlit_app.py.bak.$(date +%s)

# Check if already patched
if grep -q "show_multi_agent_analysis" web/streamlit_app.py; then
    echo "  ⚠ Multi-agent page already exists, skipping"
else
    # Add the page functions before the main() function
    # Find "def main()" and insert before it

    cat > /tmp/swarm_page.py << 'SWARMPAGE'

# ─── Multi-Agent Analysis Page ────────────────────────────────────────────

def show_multi_agent_analysis() -> None:
    """Multi-Agent KC Analysis page for disclosure documents."""
    render_brand_header(showstickman=True)
    st.markdown("<div class='aegis-panel'>", unsafe_allow_html=True)
    st.markdown("### Multi-Agent KC Analysis")
    st.markdown(
        "<div class='aegis-note'>Upload or paste police disclosure text for full 3-KC expert analysis. "
        "The system activates: (1) Disclosure Parser, (2) Query Generator, (3) Strategist KC, "
        "(4) Evidential Analyst KC, (5) Rights Guardian KC, and (6) Orchestrator.</div>",
        unsafe_allow_html=True,
    )

    input_method = st.radio(
        "Input method",
        ["Paste text", "Upload file"],
        horizontal=True,
        key="swarm_input_method",
    )

    disclosure_text = ""

    if input_method == "Paste text":
        disclosure_text = st.text_area(
            "Paste disclosure text here",
            height=400,
            key="swarm_text_input",
            placeholder="Paste Summary of Facts, charge sheet, or full disclosure here...",
        )
    else:
        uploaded_file = st.file_uploader(
            "Upload disclosure document",
            type=["txt", "pdf", "docx", "md"],
            key="swarm_file_upload",
        )
        if uploaded_file:
            try:
                disclosure_text = uploaded_file.read().decode("utf-8")
                st.success(f"Loaded {len(disclosure_text)} characters from {uploaded_file.name}")
            except Exception as e:
                st.error(f"Could not read file: {e}")

    col1, col2 = st.columns(2)
    with col1:
        analysis_type = st.selectbox(
            "Analysis depth",
            ["full", "quick", "charges_only"],
            index=0,
            key="swarm_analysis_type",
        )
    with col2:
        include_divergence = st.checkbox(
            "Include expert divergence",
            value=True,
            key="swarm_include_divergence",
        )

    if st.button("Run Multi-Agent Analysis", type="primary", use_container_width=True, key="swarm_run_btn"):
        if not disclosure_text or len(disclosure_text.strip()) < 50:
            st.warning("Please provide disclosure text (minimum 50 characters).")
            st.markdown("</div>", unsafe_allow_html=True)
            return

        def run_analysis():
            return api_call(
                "/api/v1/analyse/disclosure",
                data={
                    "disclosure_text": disclosure_text,
                    "analysis_type": analysis_type,
                    "include_expert_divergence": include_divergence,
                },
                method="POST",
                apikey=st.session_state.get("apikey"),
                sessionid=st.session_state.get("sessionid"),
                readtimeout=300,
            )

        result = run_with_stickman(
            "Running 3-KC expert analysis pipeline...",
            run_analysis,
        )

        if result and isinstance(result, dict):
            if result.get("success"):
                display_multi_agent_report(result)
            else:
                st.error(f"Analysis failed: {result.get('message', 'Unknown error')}")
        else:
            st.error("Analysis failed. Check API connection.")

    st.markdown("</div>", unsafe_allow_html=True)


def display_multi_agent_report(result: dict) -> None:
    """Display the synthesized multi-agent report."""
    st.success(f"Analysis complete in {result.get('processing_time_seconds', 0)}s ({result.get('expert_count', 3)} experts)")

    st.markdown("## Executive Summary")
    st.markdown(result.get("executive_summary", "No executive summary provided."))

    with st.expander("Disclosure Overview", expanded=False):
        st.markdown(result.get("disclosure_overview", "No overview provided."))

    with st.expander("Charge Analysis", expanded=True):
        st.markdown(result.get("charge_analysis", "No charge analysis provided."))

    with st.expander("Summary of Facts Review", expanded=False):
        st.markdown(result.get("summary_of_facts_review", "No review provided."))

    with st.expander("Police Conduct Assessment", expanded=True):
        st.markdown(result.get("police_conduct_assessment", "No assessment provided."))

    with st.expander("Further Disclosure Required", expanded=False):
        items = result.get("further_disclosure_required", [])
        if items:
            for item in items:
                st.markdown(f"- {item}")
        else:
            st.caption("No specific disclosure items identified.")

    with st.expander("Bail Analysis", expanded=False):
        st.markdown(result.get("bail_analysis", "No bail analysis provided."))

    with st.expander("Options and Recommendations", expanded=True):
        st.markdown(result.get("options_and_recommendations", "No recommendations provided."))

    with st.expander("Expert Consensus and Divergence", expanded=False):
        st.markdown(result.get("expert_consensus_and_divergence", "No consensus analysis provided."))

    with st.expander("Risk Assessment", expanded=False):
        st.markdown(result.get("risk_assessment", "No risk assessment provided."))

    st.markdown("---")
    st.markdown("### Disclaimer")
    st.warning(result.get("disclaimer", "No disclaimer provided."))

SWARMPAGE

    # Find "def main()" and insert before it
    if grep -q "def main()" web/streamlit_app.py; then
        LINENO=$(grep -n "def main()" web/streamlit_app.py | head -1 | cut -d: -f1)
        head -n $((LINENO - 1)) web/streamlit_app.py > /tmp/streamlit_top.py
        tail -n +$LINENO web/streamlit_app.py > /tmp/streamlit_bottom.py
        cat /tmp/streamlit_top.py /tmp/swarm_page.py /tmp/streamlit_bottom.py > web/streamlit_app.py
        echo "  ✓ Page functions added to web/streamlit_app.py"
    else
        cat /tmp/swarm_page.py >> web/streamlit_app.py
        echo "  ✓ Page functions appended to web/streamlit_app.py"
    fi

    # Now add navigation item
    # Find the pages list and add "Multi-Agent Analysis"
    if grep -q "Multi-Agent Analysis" web/streamlit_app.py; then
        echo "  ⚠ Navigation already patched"
    else
        # Replace the pages list in show_sidebar()
        sed -i 's/pages = \["Home", "Upload", "Collection Manager", "Search", "Analysis", "Admin Panel"\]/pages = ["Home", "Upload", "Collection Manager", "Search", "Analysis", "Multi-Agent Analysis", "Admin Panel"]/g' web/streamlit_app.py
        sed -i 's/pages = \["Home", "Upload", "Collection Manager", "Search", "Analysis"\]/pages = ["Home", "Upload", "Collection Manager", "Search", "Analysis", "Multi-Agent Analysis"]/g' web/streamlit_app.py
        sed -i 's/pages = \["Home", "Upload", "Search", "Analysis"\]/pages = ["Home", "Upload", "Search", "Analysis", "Multi-Agent Analysis"]/g' web/streamlit_app.py
        echo "  ✓ Navigation updated"
    fi

    # Add route in main()
    if grep -q 'elif page == "Multi-Agent Analysis"' web/streamlit_app.py; then
        echo "  ⚠ Route already patched"
    else
        # Find the last elif in main() and add after it
        # Find "elif page == "Admin Panel":" or the last elif
        LAST_ELIF=$(grep -n 'elif page == ' web/streamlit_app.py | tail -1 | cut -d: -f1)
        if [ -n "$LAST_ELIF" ]; then
            # Insert after the last elif block (need to find the next line that's not indented)
            # Simple approach: add before the final return or closing
            head -n $LAST_ELIF web/streamlit_app.py > /tmp/streamlit_route_top.py
            # Get the line content
            LINE_CONTENT=$(sed -n "${LAST_ELIF}p" web/streamlit_app.py)
            # Add our route after it
            echo '    elif page == "Multi-Agent Analysis":' >> /tmp/streamlit_route_top.py
            echo '        show_multi_agent_analysis()' >> /tmp/streamlit_route_top.py
            tail -n +$((LAST_ELIF + 1)) web/streamlit_app.py > /tmp/streamlit_route_bottom.py
            cat /tmp/streamlit_route_top.py /tmp/streamlit_route_bottom.py > web/streamlit_app.py
            echo "  ✓ Route added"
        fi
    fi
fi

# ─── Step 4: Verify imports ──────────────────────────────────────────────
echo ""
echo "[4/6] Verifying Python imports..."

python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from core.agent_swarm import AgentSwarm
    print('  ✓ agent_swarm imports OK')
except Exception as e:
    print(f'  ✗ agent_swarm import failed: {e}')
    sys.exit(1)

try:
    from core.rag_integration import create_swarm_rag
    print('  ✓ rag_integration imports OK')
except Exception as e:
    print(f'  ✗ rag_integration import failed: {e}')
    sys.exit(1)
" || {
    echo "ERROR: Import verification failed"
    exit 1
}

# ─── Step 5: Restart services ─────────────────────────────────────────────
echo ""
echo "[5/6] Restarting services..."

pkill -f uvicorn 2>/dev/null || true
pkill -f streamlit 2>/dev/null || true
sleep 2

echo "  Starting API server..."
nohup python3 -m uvicorn api.server:app --host 0.0.0.0 --port 8000 --log-level info > logs/api.log 2>&1 &
sleep 3

echo "  Starting Streamlit..."
nohup streamlit run web/streamlit_app.py --server.port=8501 --server.address=0.0.0.0 --server.headless=true > logs/streamlit.log 2>&1 &
sleep 3

# ─── Step 6: Verify ────────────────────────────────────────────────────────
echo ""
echo "[6/6] Verifying services..."

API_OK=false
STREAMLIT_OK=false

if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    API_OK=true
    echo "  ✓ API server running on port 8000"
else
    echo "  ✗ API server not responding"
fi

if curl -s http://localhost:8501 > /dev/null 2>&1; then
    STREAMLIT_OK=true
    echo "  ✓ Streamlit running on port 8501"
else
    echo "  ✗ Streamlit not responding"
fi

# Check endpoint exists
if [ "$API_OK" = true ]; then
    if curl -s http://localhost:8000/api/v1/analyse/disclosure -X POST -H "Content-Type: application/json" -d '{"disclosure_text":"test"}' 2>&1 | grep -q "API key required"; then
        echo "  ✓ Multi-agent endpoint exists (requires auth)"
    else
        echo "  ⚠ Endpoint status unclear"
    fi
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  Installation Complete!"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "New features:"
echo "  • Multi-Agent KC Analysis page in Streamlit"
echo "  • /api/v1/analyse/disclosure endpoint"
echo "  • 6-agent pipeline: Parser → QueryGen → 3×KC → Orchestrator"
echo ""
echo "Access:"
echo "  • Streamlit: http://localhost:8501"
echo "  • API: http://localhost:8000"
echo ""
echo "To test:"
echo "  1. Open Streamlit in browser"
echo "  2. Log in (anonymous or staff)"
echo "  3. Navigate to 'Multi-Agent Analysis'"
echo "  4. Paste disclosure text and click 'Run Multi-Agent Analysis'"
echo ""
