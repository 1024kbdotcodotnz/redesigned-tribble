#!/usr/bin/env python3
"""
NZ Legal Platform v1.5 - Online Demo App
Role-based login with temporary/permanent storage
"""

import os
import sys
import uuid
import json
from pathlib import Path
import streamlit as st
import requests
from io import BytesIO

# PDF extraction
try:
    import pypdf
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False

def extract_pdf_text(pdf_file) -> str:
    if not HAS_PYPDF:
        st.warning("pypdf not installed. Install with: pip install pypdf")
        return None
    
    try:
        pdf_reader = pypdf.PdfReader(pdf_file)
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
    page_title="NZ Legal Platform",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constants
API_URL = os.getenv("API_URL", "http://localhost:8000")


def init_session():
    """Initialize session state"""
    defaults = {
        'api_key': None,
        'tenant_info': None,
        'session_id': None,
        'chat_history': [],
        'username': '',
        'password': ''
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


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
    if st.session_state.session_id:
        headers["X-Session-ID"] = st.session_state.session_id
    
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
            st.error("Session expired. Please sign in again.")
            _do_logout(local_only=True)
            st.rerun()
            return None
        
        if response.status_code == 403:
            st.error("You do not have permission to perform this action.")
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


def _do_logout(local_only: bool = False):
    """Clear server-side session storage then local state"""
    if not local_only and st.session_state.get('session_id') and st.session_state.get('api_key'):
        # Best-effort server cleanup
        try:
            headers = {
                "Authorization": f"Bearer {st.session_state.api_key}",
                "X-Session-ID": st.session_state.session_id
            }
            requests.post(f"{API_URL}/api/v1/ingest/clear-session", headers=headers, timeout=10)
        except Exception:
            pass
    
    for key in ['api_key', 'tenant_info', 'session_id', 'chat_history', 'username', 'password']:
        if key in st.session_state:
            del st.session_state[key]
    init_session()


def login():
    """Login with username and password"""
    st.markdown("### 🔐 Demo Login")
    
    col1, col2 = st.columns(2)
    with col1:
        username = st.text_input("Username", value=st.session_state.get('username', ''))
    with col2:
        password = st.text_input("Password", type="password", value=st.session_state.get('password', ''))
    
    if st.button("Sign In", type="primary"):
        if username and password:
            try:
                response = requests.post(
                    f"{API_URL}/api/v1/login",
                    json={"username": username, "password": password},
                    timeout=15
                )
                if response.status_code == 200:
                    data = response.json()
                    st.session_state.api_key = data["api_key"]
                    st.session_state.tenant_info = data
                    st.session_state.session_id = str(uuid.uuid4())
                    st.session_state.username = username
                    st.session_state.password = password
                    st.success(f"✅ Welcome, {data.get('name', 'User')}!")
                    st.rerun()
                else:
                    st.error("Invalid username or password.")
            except Exception as e:
                st.error(f"Login failed: {str(e)}")
        else:
            st.error("Please enter both username and password.")
    
    st.markdown("---")
    st.markdown("**Demo Accounts:**")
    st.markdown("- `admin` / `demo-admin-2024!`  (Admin)")
    st.markdown("- `staff` / `demo-staff-2024!`  (Staff)")
    st.markdown("- `user` / `demo-user-2024!`    (User)")


def show_sidebar():
    """Show sidebar with tenant info, Documents menu, and navigation"""
    with st.sidebar:
        st.title("⚖️ NZ Legal Platform")
        
        tenant_info = st.session_state.get('tenant_info', {})
        role = (tenant_info.get('role') or '').lower()
        
        # Documents Upload Menu
        st.markdown("---")
        with st.expander("📂 Manage Documents", expanded=False):
            st.markdown("#### 📤 Upload Documents")
            
            # Session temporary - All users
            st.markdown("**⏳ Session Temporary** (clears on sign out)")
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
                    if result and result.get("success"):
                        st.success(f"✅ {len(documents)} files → Session DB")
                    else:
                        st.error("❌ Session upload failed")
                
                if errors:
                    st.warning(f"⚠️ Could not read: {', '.join(errors)}")
            
            if role == 'user':
                st.info("🔒 **Permanent storage is disabled for demo users.**")
                if st.button("🗑️ Clear Session Files"):
                    result = api_call("/api/v1/ingest/clear-session", "POST")
                    if result:
                        st.success("Session temporary storage cleared.")
                    else:
                        st.error("Failed to clear session storage.")
            
            # Permanent - Admin & Staff only
            if role in ('admin', 'staff'):
                st.markdown("**🏛️ Permanent DB** (Admin & Staff only)")
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
                        if result and result.get("success"):
                            st.success(f"✅ {len(documents)} files → Permanent DB")
                        else:
                            st.error("❌ Permanent upload failed")
                    
                    if errors:
                        st.warning(f"⚠️ Could not read: {', '.join(errors)}")
        
        st.markdown("---")
        
        # Tenant info display
        if tenant_info:
            st.success(f"👤 Logged in: **{tenant_info.get('name', 'User')}**")
            st.info(f"⭐ Role: **{tenant_info.get('role', 'Unknown').upper()}**")
            
            with st.expander("📊 Quota Information"):
                quotas = tenant_info.get('quotas', {})
                col1, col2, col3 = st.columns(3)
                with col1: st.metric("Queries/day", quotas.get('max_queries_per_day', 0))
                with col2: st.metric("Storage", f"{quotas.get('max_storage_bytes', 0)/1e9:.1f} GB")
                with col3: st.metric("Documents", quotas.get('max_documents', 0))
            
            if st.button("🚪 Sign Out"):
                _do_logout()
                st.rerun()
        
        st.markdown("---")
        
        # MCP Status
        st.subheader("🔗 MCP Server")
        try:
            mcp_resp = requests.get("http://localhost:8080/mcp", timeout=2)
            mcp_ok = mcp_resp.status_code in (200, 406)
        except Exception:
            mcp_ok = False
        
        if mcp_ok:
            st.success("MCP Online (port 8080)")
            st.caption("Connect: `./3_connect.sh` then use `http://localhost:8080/mcp`")
        else:
            st.warning("MCP Offline")
        
        st.markdown("---")
        
        # Navigation
        st.subheader("🌐 Navigation")
        pages = ["🏠 Home", "🔍 Search", "📊 Analysis", "📋 Similar Cases", "✅ Element Check", "📁 Upload", "📈 Usage"]
        if role == 'admin':
            pages.append("👥 Admin Panel")
        
        page = st.radio("Choose feature:", pages, index=0)
        return page


def show_upload():
    """Upload page with support for multiple files and folders"""
    st.title("📁 Document Upload")
    st.markdown("Upload legal documents to the knowledge base")
    
    # Get tenant role
    tenant_info = st.session_state.get('tenant_info', {})
    role = (tenant_info.get('role') or '').lower()
    
    # Tabs for different upload methods
    tab1, tab2, tab3 = st.tabs(["📄 Multiple Files", "📦 ZIP Archive", "ℹ️ Supported Types"])
    
    with tab1:
        render_file_upload(role)
    
    with tab2:
        render_zip_upload(role)
    
    with tab3:
        render_supported_types()


def render_file_upload(role: str):
    """Render multiple file upload interface"""
    st.subheader("Upload Multiple Files")
    
    # Collection selection based on role
    if role in ('admin', 'staff'):
        collection_options = ["user_uploads (Permanent)", "Temporary Session Storage"]
    else:
        collection_options = ["Temporary Session Storage"]
    
    collection = st.selectbox(
        "Target Collection",
        collection_options,
        key="upload_collection_select"
    )
    
    is_temporary = "Temporary" in collection
    
    if is_temporary:
        st.info("📌 Temporary files are only available for your current session.")
    else:
        st.info("🏛️ Files will be stored permanently in the knowledge base.")
    
    # Supported file extensions
    SUPPORTED_EXTENSIONS = ['pdf', 'docx', 'doc', 'txt', 'xlsx', 'xls', 'html', 'htm', 'md', 'csv', 'json']
    
    # File uploader with multiple files support
    uploaded_files = st.file_uploader(
        "Choose files to upload",
        type=SUPPORTED_EXTENSIONS,
        accept_multiple_files=True,
        key="multi_file_uploader",
        help=f"Select multiple files. Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
    )
    
    if uploaded_files:
        st.write(f"**{len(uploaded_files)} file(s) selected:**")
        
        # Show file info
        total_size = 0
        for file in uploaded_files:
            size_kb = len(file.getvalue()) / 1024
            total_size += size_kb
            cols = st.columns([3, 1, 1])
            cols[0].write(file.name)
            cols[1].code(Path(file.name).suffix.lower())
            cols[2].write(f"{size_kb:.1f} KB")
        
        st.write(f"**Total size:** {total_size:.1f} KB ({total_size/1024:.2f} MB)")
        
        # Upload button
        if st.button("🚀 Upload Files", type="primary", key="upload_files_btn"):
            with st.spinner("Uploading and processing files..."):
                upload_files_to_api(uploaded_files, is_temporary)


def render_zip_upload(role: str):
    """Render ZIP archive upload interface"""
    st.subheader("Upload Folder (ZIP Archive)")
    
    st.markdown("""
    Upload an entire folder by creating a ZIP archive:
    
    **Windows:** Right-click folder → "Send to" → "Compressed (zipped) folder"  
    **Mac:** Right-click folder → "Compress"  
    **Linux:** `zip -r my_folder.zip my_folder/`
    """)
    
    # Collection selection
    if role in ('admin', 'staff'):
        collection_options = ["user_uploads (Permanent)", "Temporary Session Storage"]
    else:
        collection_options = ["Temporary Session Storage"]
    
    collection = st.selectbox(
        "Target Collection",
        collection_options,
        key="zip_collection_select"
    )
    
    is_temporary = "Temporary" in collection
    
    # ZIP file uploader
    zip_file = st.file_uploader(
        "Choose ZIP archive",
        type=["zip"],
        key="zip_uploader"
    )
    
    if zip_file:
        # Preview ZIP contents
        try:
            import zipfile
            import io
            with zipfile.ZipFile(io.BytesIO(zip_file.getvalue())) as zf:
                files = [f for f in zf.namelist() if not f.endswith('/')]
                SUPPORTED_EXTENSIONS = ['.pdf', '.docx', '.doc', '.txt', '.xlsx', '.xls', '.html', '.htm', '.md', '.csv', '.json']
                supported_files = [f for f in files if any(f.lower().endswith(ext) for ext in SUPPORTED_EXTENSIONS)]
                
                st.write(f"**Archive contains {len(files)} items:**")
                st.write(f"- ✅ {len(supported_files)} supported files will be processed")
                st.write(f"- ⚠️ {len(files) - len(supported_files)} items skipped (unsupported or folders)")
                
                with st.expander(f"View files ({len(supported_files)} supported)"):
                    for f in supported_files[:20]:
                        st.text(f)
                    if len(supported_files) > 20:
                        st.text(f"... and {len(supported_files) - 20} more")
        except zipfile.BadZipFile:
            st.error("❌ Invalid ZIP file")
            return
        
        zip_file.seek(0)
        
        if st.button("🚀 Upload ZIP Archive", type="primary", key="upload_zip_btn"):
            with st.spinner("Extracting and processing files..."):
                upload_zip_to_api(zip_file, is_temporary)


def render_supported_types():
    """Display supported file types"""
    st.subheader("Supported File Types")
    
    file_types = {
        "📄 Documents": [
            (".pdf", "PDF documents", "Fully supported with page extraction"),
            (".docx", "Microsoft Word", "Modern Word format (.docx)"),
            (".doc", "Microsoft Word (Old)", "Legacy format (requires antiword)"),
            (".txt", "Plain Text", "UTF-8 encoded text files"),
            (".md", "Markdown", "Markdown formatted text"),
        ],
        "📊 Spreadsheets": [
            (".xlsx", "Excel", "Modern Excel format (.xlsx)"),
            (".xls", "Excel (Old)", "Legacy Excel format"),
            (".csv", "CSV", "Comma-separated values"),
        ],
        "🌐 Web & Data": [
            (".html", "HTML", "Web pages"),
            (".htm", "HTML", "Web pages (alternate extension)"),
            (".json", "JSON", "JSON data files"),
        ],
    }
    
    for category, types in file_types.items():
        st.markdown(f"**{category}**")
        for ext, name, desc in types:
            st.markdown(f"  - `{ext}` - {name}: {desc}")
        st.write("")
    
    st.info("""
    **Upload Limits:**
    - Maximum 50 files per upload
    - Maximum 100 MB per ZIP archive
    - Files are chunked and embedded for semantic search
    """)


def upload_files_to_api(files, is_temporary: bool):
    """Upload multiple files to the API"""
    if not st.session_state.get("api_key"):
        st.error("❌ Not authenticated")
        return
    
    headers = {"Authorization": f"Bearer {st.session_state.api_key}"}
    
    try:
        # Prepare files for upload
        upload_files = []
        for f in files:
            f.seek(0)
            mime = get_mime_type(f.name)
            upload_files.append(("files", (f.name, f.getvalue(), mime)))
        
        data = {"collection": "temp_session" if is_temporary else "user_uploads"}
        
        response = requests.post(
            f"{API_URL}/api/v1/upload/files",
            headers=headers,
            files=upload_files,
            data=data,
            timeout=120
        )
        
        if response.status_code == 200:
            display_upload_result(response.json())
        else:
            st.error(f"❌ Upload failed: {response.status_code}")
            try:
                st.error(response.json().get("detail", "Unknown error"))
            except:
                st.error(response.text[:500])
    
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")


def upload_zip_to_api(zip_file, is_temporary: bool):
    """Upload ZIP archive to the API"""
    if not st.session_state.get("api_key"):
        st.error("❌ Not authenticated")
        return
    
    headers = {"Authorization": f"Bearer {st.session_state.api_key}"}
    
    try:
        zip_file.seek(0)
        files = {"file": (zip_file.name, zip_file.getvalue(), "application/zip")}
        data = {"collection": "temp_session" if is_temporary else "user_uploads"}
        
        response = requests.post(
            f"{API_URL}/api/v1/upload/zip",
            headers=headers,
            files=files,
            data=data,
            timeout=180
        )
        
        if response.status_code == 200:
            display_upload_result(response.json())
        else:
            st.error(f"❌ Upload failed: {response.status_code}")
            try:
                st.error(response.json().get("detail", "Unknown error"))
            except:
                st.error(response.text[:500])
    
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")


def get_mime_type(filename: str) -> str:
    """Get MIME type for file"""
    ext = Path(filename).suffix.lower()
    mime_types = {
        '.pdf': 'application/pdf',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.xls': 'application/vnd.ms-excel',
        '.txt': 'text/plain',
        '.html': 'text/html',
        '.htm': 'text/html',
        '.md': 'text/markdown',
        '.csv': 'text/csv',
        '.json': 'application/json',
    }
    return mime_types.get(ext, 'application/octet-stream')


def display_upload_result(result):
    """Display upload result"""
    if result.get("success"):
        st.success(f"✅ {result['message']}")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Files Processed", result.get("files_processed", 0))
        col2.metric("Files Failed", result.get("files_failed", 0))
        col3.metric("Total Chunks", result.get("total_chunks", 0))
        
        if result.get("details"):
            with st.expander("View Details"):
                for detail in result["details"]:
                    status = detail.get("status", "unknown")
                    filename = detail.get("filename", "unknown")
                    
                    if status == "success":
                        st.success(f"✅ {filename}")
                        cols = st.columns(4)
                        cols[0].write(f"Type: {detail.get('type', 'unknown')}")
                        cols[1].write(f"Words: {detail.get('words', 0)}")
                        if "pages" in detail:
                            cols[2].write(f"Pages: {detail['pages']}")
                        if "sheets" in detail:
                            cols[2].write(f"Sheets: {detail['sheets']}")
                    else:
                        st.error(f"❌ {filename}: {detail.get('error', 'Unknown error')}")
    else:
        st.error(f"❌ {result.get('message', 'Upload failed')}")


def show_home():
    """Home page with detailed database statistics"""
    st.title("⚖️ NZ Legal Platform")
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
        
        # Summary metrics
        # Determine status from API response (status field at root level)
        is_healthy = stats.get('status') == 'healthy'
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Documents", f"{db.get('total_documents', 0):,}")
        with col2:
            st.metric("Collections", len(db.get('collections', {})))
        with col3:
            st.metric("Status", "🟢 Online" if is_healthy else "🔴 Offline")
        
        st.markdown("---")
        
        # Detailed collection breakdown
        st.subheader("📁 Collections Overview")
        collections = db.get('collections', {})
        
        if collections:
            # Define category groupings
            category_groups = {
                "📜 Legislation": ['nz_legislation', 'nz_legislation_detailed'],
                "⚖️ Case Law": ['nz_case_law', 'nzlii_criminal_cases', 'nz_criminal_cases'],
                "👮 Police & Procedures": ['nz_police_manual', 'nz_police_procedures'],
                "📚 General": ['nz_legal_unified', 'uncategorized'],
                "👤 User Content": ['user_uploads', 'user_documents'],
            }
            
            for group_name, collection_names in category_groups.items():
                group_collections = []
                group_total = 0
                
                for coll_name in collection_names:
                    if coll_name in collections:
                        coll_data = collections[coll_name]
                        count = coll_data.get('count', 0) if isinstance(coll_data, dict) else coll_data
                        if count > 0:
                            group_collections.append((coll_name, count))
                            group_total += count
                
                if group_collections:
                    with st.expander(f"**{group_name}** — {group_total:,} documents", expanded=True):
                        cols = st.columns(len(group_collections) if len(group_collections) <= 4 else 4)
                        for idx, (coll_name, count) in enumerate(group_collections):
                            col_idx = idx % 4
                            with cols[col_idx]:
                                display_name = coll_name.replace('nz_', '').replace('_', ' ').title()
                                st.metric(display_name, f"{count:,}")
        else:
            st.info("No collection data available")
            
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
            ["nz_legislation", "nzlii_criminal_cases", "nz_legal_unified"],
            default=["nz_legislation", "nzlii_criminal_cases"]
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
                    if 'satisfied' in status or 'met' in status or 'proven' in status:
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


def show_admin_panel():
    """Admin panel page"""
    st.title("👥 Admin Panel")
    
    tenant_info = st.session_state.get('tenant_info', {})
    if tenant_info.get('role') != 'admin':
        st.error("Admin access required")
        return
    
    st.subheader("Demo Users")
    admin_key = os.getenv("ADMIN_API_KEY", "dev-key-change-in-production")
    result = api_call(f"/api/v1/admin/tenants?admin_key={admin_key}")
    
    if result and 'tenants' in result:
        for t in result['tenants']:
            with st.expander(f"{t.get('username')} — {t.get('name')} ({t.get('role')})"):
                st.json(t)
    else:
        st.warning("Unable to load tenant list")


def main():
    """Main application function"""
    init_session()
    
    if not st.session_state.get('api_key'):
        st.title("⚖️ NZ Legal Platform")
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
    elif page == "📁 Upload":
        show_upload()
    elif page == "📈 Usage":
        show_usage()
    elif page == "👥 Admin Panel":
        show_admin_panel()


if __name__ == "__main__":
    main()
