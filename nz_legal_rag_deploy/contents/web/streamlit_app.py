#!/usr/bin/env python3
"""
NZ Legal RAG v1.4 - Robust PDF Extraction + Error Handling
"""

import os
import sys
import json
from pathlib import Path
import streamlit as st
import requests
from io import BytesIO

# PDF extraction
# PDF extraction
try:
    import pypdf
    HAS_PYPDF = True  # Fixed: PYPDF (uppercase)
except ImportError:
    HAS_PYPDF = False

def extract_pdf_text(pdf_file) -> str:
    if not HAS_PYPDF:
        st.warning("pypdf not installed. Install with: pip install pypdf")
        return None
    
    try:
        pdf_reader = pypdf.PdfReader(pdf_file)  # Fixed: pypdf.PdfReader
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        st.error(f"PDF extraction failed: {str(e)}")
        return None

# DOCX extraction
HAS_DOCX = False
def import_docx():
    global HAS_DOCX
    try:
        from docx import Document
        HAS_DOCX = True
        return Document
    except ImportError:
        HAS_DOCX = False
        return None

# Add parent to path for custom modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Page config
st.set_page_config(
    page_title="NZ Legal RAG",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constants
API_URL = os.getenv("API_URL", "http://localhost:8000")


def init_session():
    """Initialize session state"""
    if 'api_key' not in st.session_state:
        st.session_state.api_key = None
    if 'tenant_info' not in st.session_state:
        st.session_state.tenant_info = None
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []

def extract_file_text(f) -> str:
    """Extract text from any uploaded file (PDF, TXT, DOCX, JSON, MD)"""
    file_ext = Path(f.name).suffix.lower()
    
    try:
        if file_ext == '.pdf':
            return extract_pdf_text(f)
        
        elif file_ext in ['.txt', '.json', '.md']:
            return f.getvalue().decode('utf-8')
        
        elif file_ext == '.docx':
            Document = import_docx()
            if Document:
                doc = Document(BytesIO(f.getvalue()))
                text = "\n".join([para.text for para in doc.paragraphs])
                return text.strip()
            else:
                st.error("python-docx not installed. Install with: pip install python-docx")
                return None
        
        else:
            st.error(f"Unsupported file type: {file_ext}")
            return None
    
    except Exception as e:
        st.error(f"Cannot read {f.name}: {str(e)}")
        return None


def api_call(endpoint: str, method: str = "GET", data: dict = None) -> dict | None:
    """Make API call with authentication and error handling"""
    headers = {}
    if st.session_state.api_key:
        headers["Authorization"] = f"Bearer {st.session_state.api_key}"
    
    url = f"{API_URL}{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=30)
        elif method == "POST":
            response = requests.post(url, json=data, headers=headers, timeout=60)
        else:
            st.error(f"Unsupported HTTP method: {method}")
            return None
        
        if response.status_code == 401:
            st.error("Invalid API key. Please check your credentials.")
            st.session_state.api_key = None
            st.session_state.tenant_info = None
            st.rerun()
            return None
        
        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to API server. Check if server is running at " + API_URL)
        return None
    except requests.exceptions.Timeout:
        st.error("Request timed out. Please try again.")
        return None
    except Exception as e:
        st.error(f"API error: {str(e)}")
        return None


def login():
    """Login with API key"""
    st.markdown("### 🔐 Authentication")
    
    api_key = st.text_input(
        "Enter your API Key",
        type="password",
        help="Enter your API key to access the legal database"
    )
    
    if st.button("Sign In", type="primary"):
        if api_key:
            st.session_state.api_key = api_key
            tenant_info = api_call("/api/v1/tenant/me")
            
            if tenant_info:
                st.session_state.tenant_info = tenant_info
                st.success(f"✅ Welcome, {tenant_info.get('name', 'User')}!")
                st.rerun()
            else:
                st.error("Login failed. Check API key.")
        else:
            st.error("Please enter an API key")


def show_sidebar():
    """Show sidebar with tenant info, Documents menu, and navigation"""
    with st.sidebar:
        st.title("⚖️ NZ Legal RAG")
        
        # Documents Upload Menu
        st.markdown("---")
        with st.expander("📂 Manage Documents", expanded=False):
            st.markdown("#### 📤 Upload Documents")
            
            # Session temporary - All users
            st.markdown("**⏳ Session Temporary** (clears on restart)")
            temp_files = st.file_uploader(
                "Upload personal/private files", 
                type=['pdf', 'docx', 'txt', 'json', 'md'],
                accept_multiple_files=True,
                key="session_upload"
            )
            
            if temp_files and st.button("💾 Save to Session DB", key="save_session"):
                documents = []
                errors = []
                
                for f in temp_files:
                    content = extract_file_text(f)
                    if content:
                        documents.append({"name": f.name, "content": content})
                    else:
                        errors.append(f.name)
                
                if documents:
                    result = api_call("/api/v1/ingest/temporary", "POST", {"documents": documents})
                    if result:
                        st.success(f"✅ {len(documents)} files → Session DB")
                    else:
                        st.error("❌ Session upload failed")
                
                if errors:
                    st.warning(f"⚠️ Could not read: {', '.join(errors)}")
            
            # Permanent - Professional Tier only
            if st.session_state.get('tenant_info'):
                tenant_info = st.session_state.tenant_info
                tier = tenant_info.get("tier", "").lower()
                is_professional = tier == "professional"
                
                if is_professional:
                    st.markdown("**🏛️ Permanent DB** (Professional Tier)")
                    perm_files = st.file_uploader(
                        "Upload official documents", 
                        type=['pdf', 'docx', 'txt', 'json'],
                        accept_multiple_files=True,
                        key="permanent_upload"
                    )
                    
                    if perm_files and st.button("💾 Save to Permanent DB", key="save_permanent"):
                        documents = []
                        errors = []
                        
                        for f in perm_files:
                            content = extract_file_text(f)
                            if content:
                                documents.append({"name": f.name, "content": content})
                            else:
                                errors.append(f.name)
                        
                        if documents:
                            result = api_call("/api/v1/ingest/permanent", "POST", {"documents": documents})
                            if result:
                                st.success(f"✅ {len(documents)} files → Permanent DB")
                            else:
                                st.error("❌ Permanent upload failed")
                        
                        if errors:
                            st.warning(f"⚠️ Could not read: {', '.join(errors)}")
                else:
                    st.info("🔒 **Permanent storage**: Professional Tier only")
        
        st.markdown("---")
        
        # Tenant info display
        if st.session_state.get('tenant_info'):
            tenant = st.session_state.tenant_info
            st.success(f"👤 Logged in: **{tenant.get('name', 'User')}**")
            st.info(f"⭐ Tier: **{tenant.get('tier', 'Unknown').upper()}**")
            
            with st.expander("📊 Quota Information"):
                quotas = tenant.get('quotas', {})
                col1, col2, col3 = st.columns(3)
                with col1: st.metric("Queries/day", quotas.get('max_queries_per_day', 0))
                with col2: st.metric("Storage", f"{quotas.get('max_storage_bytes', 0)/1e9:.1f} GB")
                with col3: st.metric("Documents", quotas.get('max_documents', 0))
            
            if st.button("🚪 Sign Out"):
                for key in ['api_key', 'tenant_info', 'chat_history']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
        
        st.markdown("---")
        
        # Navigation
        st.subheader("🌐 Navigation")
        page = st.radio(
            "Choose feature:",
            ["🏠 Home", "🔍 Search", "📊 Analysis", "📋 Similar Cases", "✅ Element Check", "📈 Usage"],
            index=0
        )
        return page


def show_home():
    """Home page with stats"""
    st.title("⚖️ NZ Legal RAG")
    st.markdown("### New Zealand Legal Research Assistant")
    
    st.markdown("""
    **Powered by RAG (Retrieval Augmented Generation) with:**
    - 🏛️ **Legislation** (Acts & Regulations)
    - ⚖️ **Case Law** (NZLII precedents) 
    - 👮 **Police Manual** (Procedures & policies)
    - 🤖 **AI Analysis** (context-aware responses)
    """)
    
    st.markdown("---")
    
    st.subheader("📊 Database Status")
    stats = api_call("/health")
    if stats and isinstance(stats, dict) and 'database' in stats:
        db = stats['database']
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Documents", f"{db.get('total_documents', 0):,}")
        with col2:
            st.metric("Collections", len(db.get('collections', {})))
        with col3:
            st.metric("Status", "🟢 Online" if db.get('healthy', False) else "🔴 Offline")
    else:
        st.warning("Cannot fetch database stats. Check API connection.")


def show_search():
    """Search page"""
    st.title("🔍 Search Legal Database")
    
    col1, col2 = st.columns([3,1])
    with col1:
        query = st.text_input("Enter search query:", placeholder="e.g., search warrant requirements")
    with col2:
        top_k = st.slider("Max results:", 3, 50, 10)
    
    col1, col2 = st.columns(2)
    with col1:
        collections = st.multiselect(
            "Filter collections:", 
            ["legislation", "case_law", "police_manual"],
            default=["legislation", "case_law"]
        )
    with col2:
        st.caption("Leave empty for all collections")
    
    if st.button("🔎 Search", type="primary") and query.strip():
        with st.spinner("Searching database..."):
            result = api_call("/api/v1/search", "POST", {
                "query": query.strip(),
                "collections": collections if collections else None, 
                "top_k": top_k
            })
            if result and isinstance(result, dict):
                st.success(f"✅ Found **{result.get('total', 0)}** results")
                for i, item in enumerate(result.get('results', []), 1):
                    title = item.get('metadata', {}).get('title', f'Result {i}')
                    with st.expander(f"[{i}] {title}"):
                        content = item.get('document', '')[:2000]
                        st.markdown(content + ("..." if len(item.get('document', '')) > 2000 else ""))
                        if 'metadata' in item:
                            with st.expander("Metadata"):
                                st.json(item['metadata'])
            else:
                st.error("No results or search failed")


def show_analysis():
    """Legal analysis page"""
    st.title("📊 Legal Analysis")
    
    col1, col2 = st.columns(2)
    with col1:
        analysis_type = st.selectbox(
            "Analysis type:",
            ["general", "charge_review", "search_warrant", "evidence_review"]
        )
    with col2:
        st.info("Select type and enter your question")
    
    query = st.text_area(
        "Your question:", 
        placeholder="e.g., What are the requirements for a search warrant under the Search and Surveillance Act?",
        height=120
    )
    
    if st.button("🤖 Analyze", type="primary") and query.strip():
        with st.spinner("Analyzing..."):
            result = api_call("/api/v1/analyze", "POST", {
                "query": query.strip(),
                "analysis_type": analysis_type
            })
            if result and 'answer' in result:
                st.markdown("### 📝 Analysis Result")
                st.markdown(result['answer'])
            else:
                st.error("Analysis failed")


def show_similar_cases():
    """Similar cases page"""
    st.title("📋 Find Similar Cases")
    st.markdown("Enter case facts to find similar precedents")
    
    facts = st.text_area(
        "Case facts:", 
        placeholder="e.g., Defendant was found with 5g of methamphetamine in vehicle during traffic stop...",
        height=150
    )
    
    if st.button("🔍 Find Similar Cases", type="primary") and facts.strip():
        with st.spinner("Finding similar cases..."):
            result = api_call("/api/v1/similar-cases", "POST", {"facts": facts.strip()})
            if result and 'results' in result:
                for i, case in enumerate(result['results'], 1):
                    with st.expander(f"**Case {i}**: {case.get('title', 'Untitled')}"):
                        st.markdown(case.get('summary', ''))
                        st.caption(case.get('citation', ''))
            else:
                st.info("No similar cases found")


def show_element_check():
    """Element check page"""
    st.title("✅ Charge Element Check")
    st.markdown("Check if facts satisfy elements of an offense")
    
    col1, col2 = st.columns(2)
    with col1:
        offense = st.text_input("Offense name:", placeholder="e.g., Possession for Supply (Misuse of Drugs Act)")
    with col2:
        st.info("Enter offense and facts below")
    
    facts = st.text_area("Facts of case:", height=150)
    
    if st.button("✅ Check Elements", type="primary") and offense.strip() and facts.strip():
        with st.spinner("Checking elements..."):
            result = api_call("/api/v1/check-elements", "POST", {
                "offense": offense.strip(),
                "facts": facts.strip()
            })
            if result and 'elements' in result:
                st.markdown("### 📋 Element Analysis")
                for elem in result['elements']:
                    status = elem.get('status', '').lower()
                    if 'satisfied' in status or 'met' in status:
                        st.success(f"✅ **{elem.get('element', '')}**")
                        st.caption(elem.get('reasoning', ''))
                    else:
                        st.error(f"❌ **{elem.get('element', '')}**")
                        st.caption(elem.get('reasoning', ''))
            else:
                st.error("Element check failed")


def show_usage():
    """Usage analytics page"""
    st.title("📈 Usage Analytics")
    
    col1, col2 = st.columns(2)
    with col1:
        days = st.slider("Show last X days:", 7, 90, 30)
    with col2:
        st.metric("Refresh", "Auto")
    
    result = api_call(f"/api/v1/tenant/usage?days={days}")
    if result:
        summary = result.get('summary', {})
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Queries", summary.get('total_queries', 0))
        with col2:
            st.metric("Storage Used", f"{summary.get('storage_bytes_used', 0)/1e9:.2f} GB")
        with col3:
            st.metric("Documents", summary.get('document_count', 0))
        
        if 'daily_usage' in result:
            st.subheader("Daily Breakdown")
            st.bar_chart(result['daily_usage'])
    else:
        st.warning("Cannot fetch usage data")


def main():
    """Main application function"""
    init_session()
    
    if not st.session_state.get('api_key'):
        st.title("⚖️ NZ Legal RAG")
        login()
        return
    
    page = show_sidebar()
    
    if page == "🏠 Home":
        show_home()
    elif page == "🔍 Search":
        show_search()
    elif page == "📊 Analysis":
        show_analysis()
    elif page == "📋 Similar Cases":
        show_similar_cases()
    elif page == "✅ Element Check":
        show_element_check()
    elif page == "📈 Usage":
        show_usage()


if __name__ == "__main__":
    main()

