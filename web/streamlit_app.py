#!/usr/bin/env python3
"""
NZ Legal RAG Web Interface
Streamlit-based UI for legal research
"""

import os
import sys
import json
from pathlib import Path

import streamlit as st
import requests

# Add parent to path
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


def api_call(endpoint: str, method: str = "GET", data: dict = None) -> dict:
    """Make API call with authentication"""
    headers = {}
    if st.session_state.api_key:
        headers["Authorization"] = f"Bearer {st.session_state.api_key}"
    
    url = f"{API_URL}{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=30)
        else:
            response = requests.post(url, json=data, headers=headers, timeout=60)
        
        if response.status_code == 401:
            st.error("Invalid API key. Please check your credentials.")
            st.session_state.api_key = None
            st.session_state.tenant_info = None
            return None
        
        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to API server. Please check that the server is running.")
        return None
    except requests.exceptions.Timeout:
        st.error("Request timed out. Please try again.")
        return None
    except Exception as e:
        st.error(f"API error: {str(e)}")
        return None


def login():
    """Login with API key"""
    st.subheader("🔐 Authentication")
    
    api_key = st.text_input(
        "Enter your API Key",
        type="password",
        help="Enter your API key to access the legal database"
    )
    
    if st.button("Sign In"):
        if api_key:
            # Test the API key
            st.session_state.api_key = api_key
            tenant_info = api_call("/api/v1/tenant/me")
            
            if tenant_info:
                st.session_state.tenant_info = tenant_info
                st.success(f"Welcome, {tenant_info['name']}!")
                st.rerun()
        else:
            st.error("Please enter an API key")


def show_sidebar():
    """Show sidebar with tenant info and navigation"""
    with st.sidebar:
        st.title("⚖️ NZ Legal RAG")
        
        if st.session_state.tenant_info:
            tenant = st.session_state.tenant_info
            
            st.success(f"Logged in as: {tenant['name']}")
            st.info(f"Tier: {tenant['tier'].upper()}")
            
            with st.expander("Quota Information"):
                quotas = tenant['quotas']
                st.write(f"📊 Max queries/day: {quotas['max_queries_per_day']:,}")
                st.write(f"💾 Max storage: {quotas['max_storage_bytes'] / 1e9:.1f} GB")
                st.write(f"📄 Max documents: {quotas['max_documents']:,}")
            
            if st.button("🚪 Sign Out"):
                st.session_state.api_key = None
                st.session_state.tenant_info = None
                st.session_state.chat_history = []
                st.rerun()
        
        st.divider()
        
        # Navigation
        st.subheader("Navigation")
        page = st.radio(
            "Select a feature:",
            ["🏠 Home", "🔍 Search", "📊 Legal Analysis", "📋 Similar Cases", "✅ Element Check", "📈 Usage"]
        )
        
        return page


def show_home():
    """Show home page"""
    st.title("⚖️ NZ Legal RAG")
    st.subheader("New Zealand Legal Research Assistant")
    
    st.markdown("""
    Welcome to the NZ Legal RAG system. This tool helps you research New Zealand law using:
    
    - **Legislation**: Acts and Regulations from legislation.govt.nz
    - **Case Law**: Precedents from NZLII
    - **Police Manual**: Procedures and policies
    - **Legal Analysis**: AI-powered analysis of legal questions
    
    ### Features
    
    🔍 **Search** - Find relevant legislation and case law
    
    📊 **Legal Analysis** - Get AI-powered analysis of legal questions
    
    📋 **Similar Cases** - Find cases with similar fact patterns
    
    ✅ **Element Check** - Check if facts satisfy legal elements
    
    📈 **Usage** - View your usage statistics
    """)
    
    # Show database stats
    st.subheader("Database Statistics")
    stats = api_call("/health")
    if stats and 'database' in stats:
        db = stats['database']
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Documents", f"{db.get('total_documents', 0):,}")
        with col2:
            colls = len(db.get('collections', {}))
            st.metric("Collections", colls)
        with col3:
            st.metric("Status", "✅ Online")


def show_search():
    """Show search page"""
    st.title("🔍 Search Legal Database")
    
    query = st.text_input("Enter your search query:", 
                         placeholder="e.g., search warrant requirements section 21 BORA")
    
    col1, col2 = st.columns(2)
    
    with col1:
        collections = st.multiselect(
            "Collections to search:",
            ["legislation", "case_law", "police_manual", "legal_research"],
            default=None,
            help="Leave empty to search all collections"
        )
    
    with col2:
        top_k = st.slider("Number of results:", 5, 50, 10)
    
    if st.button("Search", type="primary"):
        if not query:
            st.warning("Please enter a search query")
            return
        
        with st.spinner("Searching..."):
            result = api_call("/api/v1/search", "POST", {
                "query": query,
                "collections": collections if collections else None,
                "top_k": top_k
            })
        
        if result:
            st.success(f"Found {result['total']} results")
            
            for i, item in enumerate(result['results'], 1):
                with st.expander(f"[{i}] {item['metadata'].get('title', 'Unknown')} (Relevance: {item['relevance']:.1%})"):
                    st.markdown(f"**Category:** {item['metadata'].get('category', 'Unknown')}")
                    st.markdown(f"**Source:** {item['metadata'].get('source', 'Unknown')}")
                    st.divider()
                    st.markdown(item['document'])


def show_analysis():
    """Show legal analysis page"""
    st.title("📊 Legal Analysis")
    
    analysis_type = st.selectbox(
        "Type of Analysis:",
        [
            ("general", "General Legal Analysis"),
            ("charge_review", "Charge Review - Analyze charges against evidence"),
            ("search_warrant", "Search Warrant - Evaluate warrant validity"),
            ("disclosure_review", "Disclosure Review - Check disclosure compliance")
        ],
        format_func=lambda x: x[1]
    )[0]
    
    query = st.text_area(
        "Enter your legal question or scenario:",
        height=100,
        placeholder="Describe the legal issue you need analyzed..."
    )
    
    context = st.text_area(
        "Additional context (optional):",
        height=80,
        placeholder="Any additional facts or background information..."
    )
    
    if st.button("Analyze", type="primary"):
        if not query:
            st.warning("Please enter a legal question")
            return
        
        with st.spinner("Performing legal analysis... This may take a moment."):
            result = api_call("/api/v1/analyze", "POST", {
                "query": query,
                "analysis_type": analysis_type,
                "context": context if context else None
            })
        
        if result:
            st.success(f"Analysis complete (Confidence: {result['confidence']:.0%})")
            
            # Display answer
            st.subheader("Analysis")
            st.markdown(result['answer'])
            
            # Display citations
            if result['citations']:
                st.subheader("Citations")
                for citation in result['citations']:
                    st.markdown(f"• {citation}")
            
            # Display sources
            with st.expander("View Sources"):
                for source in result['sources']:
                    st.markdown(f"**{source['title']}** ({source['category']})")
                    st.markdown(f"Relevance: {source['relevance']:.1%}")
                    st.divider()


def show_similar_cases():
    """Show similar cases page"""
    st.title("📋 Find Similar Cases")
    
    st.markdown("""
    Enter the facts of a case to find precedents with similar fact patterns or legal issues.
    """)
    
    facts = st.text_area(
        "Case Facts:",
        height=150,
        placeholder="Describe the facts of the case..."
    )
    
    legal_issue = st.text_input(
        "Legal Issue (optional):",
        placeholder="e.g., unreasonable search, confession reliability"
    )
    
    top_k = st.slider("Number of cases:", 3, 20, 5)
    
    if st.button("Find Similar Cases", type="primary"):
        if not facts:
            st.warning("Please enter case facts")
            return
        
        with st.spinner("Searching for similar cases..."):
            result = api_call("/api/v1/similar-cases", "POST", {
                "facts": facts,
                "legal_issue": legal_issue if legal_issue else None,
                "top_k": top_k
            })
        
        if result:
            st.success(f"Found {len(result['results'])} similar cases")
            
            for i, case in enumerate(result['results'], 1):
                with st.expander(f"[{i}] {case['title']}" if case['title'] != 'Unknown' else f"[{i}] Case {i}"):
                    cols = st.columns(2)
                    with cols[0]:
                        st.markdown(f"**Court:** {case['court']}")
                        if case['year']:
                            st.markdown(f"**Year:** {case['year']}")
                    with cols[1]:
                        st.markdown(f"**Citation:** {case['citation'] or 'N/A'}")
                        st.markdown(f"**Similarity:** {case['relevance']:.1%}")
                    
                    st.divider()
                    st.markdown(case['summary'])


def show_element_check():
    """Show element check page"""
    st.title("✅ Legal Element Check")
    
    st.markdown("""
    Check whether the facts of a case satisfy the legal elements of an offense.
    """
    )
    
    offense = st.text_input(
        "Offense Name:",
        placeholder="e.g., possession for supply Class A drug"
    )
    
    statute = st.text_input(
        "Statute (optional):",
        placeholder="e.g., Misuse of Drugs Act 1975, s 6(1)(a)"
    )
    
    facts = st.text_area(
        "Facts of the Case:",
        height=200,
        placeholder="Describe the facts that have been established or alleged..."
    )
    
    if st.button("Check Elements", type="primary"):
        if not offense or not facts:
            st.warning("Please enter both offense and facts")
            return
        
        with st.spinner("Analyzing elements..."):
            result = api_call("/api/v1/check-elements", "POST", {
                "offense": offense,
                "facts": facts,
                "statute": statute if statute else None
            })
        
        if result:
            st.subheader(f"Element Analysis: {result['offense']}")
            
            if 'elements' in result and result['elements']:
                for elem in result['elements']:
                    status = elem.get('status', 'Unknown')
                    
                    # Color code based on status
                    if 'proven' in status.lower() or 'satisfied' in status.lower():
                        st.success(f"✅ **{elem['element']}**\n\n{status}")
                    elif 'unclear' in status.lower() or 'unknown' in status.lower():
                        st.warning(f"⚠️ **{elem['element']}**\n\n{status}")
                    else:
                        st.error(f"❌ **{elem['element']}**\n\n{status}")
            
            with st.expander("Full Analysis"):
                st.markdown(result['analysis'])


def show_usage():
    """Show usage page"""
    st.title("📈 Usage Statistics")
    
    days = st.select_slider(
        "Period:",
        options=[7, 14, 30, 60, 90],
        value=30
    )
    
    if st.button("Refresh"):
        with st.spinner("Loading usage data..."):
            result = api_call(f"/api/v1/tenant/usage?days={days}")
        
        if result:
            st.subheader("Summary")
            
            cols = st.columns(3)
            summary = result['summary']
            
            with cols[0]:
                st.metric("Total Queries", f"{summary['total_queries']:,}")
            with cols[1]:
                st.metric("API Calls", f"{summary['total_api_calls']:,}")
            with cols[2]:
                storage_gb = summary['storage_bytes_used'] / 1e9
                st.metric("Storage Used", f"{storage_gb:.2f} GB")
            
            if result['daily_breakdown']:
                st.subheader("Daily Breakdown")
                
                import pandas as pd
                
                df = pd.DataFrame(result['daily_breakdown'])
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date')
                
                st.line_chart(df.set_index('date')[['queries', 'api_calls']])


def main():
    """Main application"""
    init_session()
    
    # Check if logged in
    if not st.session_state.api_key:
        login()
        return
    
    # Show sidebar and get selected page
    page = show_sidebar()
    
    # Route to page
    if page == "🏠 Home":
        show_home()
    elif page == "🔍 Search":
        show_search()
    elif page == "📊 Legal Analysis":
        show_analysis()
    elif page == "📋 Similar Cases":
        show_similar_cases()
    elif page == "✅ Element Check":
        show_element_check()
    elif page == "📈 Usage":
        show_usage()


if __name__ == "__main__":
    main()
