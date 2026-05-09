#!/usr/bin/env python3
"""
NZ Legal Platform v1.5 - Online Demo App
Role-based login with temporary/permanent storage
"""

import os
import re
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
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------------------------------------------------------
# Custom CSS – deep navy sidebar, clean cards, modern typography
# ------------------------------------------------------------------
st.html("""
<style>
/* One font everywhere. No decorative nonsense. */
html, body, [class*="css"], h1, h2, h3, h4, h5, h6, p, li, label, button, input, textarea {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
    -webkit-font-smoothing: antialiased;
}

/* Tighten everything up */
[data-testid="stAppViewContainer"] { background: #fff !important; }
[data-testid="stSidebar"] { background: #f5f5f5 !important; border-right: 1px solid #ddd !important; }

/* Compact headings */
h1 { font-size: 1.4rem !important; font-weight: 600 !important; margin-bottom: 0.5rem !important; }
h2 { font-size: 1.15rem !important; font-weight: 600 !important; margin-bottom: 0.4rem !important; }
h3 { font-size: 1rem !important; font-weight: 600 !important; margin-bottom: 0.3rem !important; }

/* Compact body text */
p, li { font-size: 0.9rem !important; line-height: 1.5 !important; }

/* Buttons - flat, sharp, high contrast */
.stButton > button {
    background: #3b5998 !important;
    border: none !important;
    border-radius: 2px !important;
    padding: 0.4rem 1rem !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
    text-shadow: none !important;
}
.stButton > button,
.stButton > button * {
    color: #ffffff !important;
}
.stButton > button:hover {
    background: #4a6fa5 !important;
}
.stButton > button:hover,
.stButton > button:hover * {
    color: #ffffff !important;
}
.stButton > button[kind="secondary"] {
    background: transparent !important;
    border: 1px solid #3b5998 !important;
}
.stButton > button[kind="secondary"],
.stButton > button[kind="secondary"] * {
    color: #3b5998 !important;
}

/* Inputs - clean borders */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    border: 1px solid #ccc !important;
    border-radius: 2px !important;
    font-size: 0.9rem !important;
    padding: 0.4rem 0.6rem !important;
}

/* Remove excessive metric card styling */
[data-testid="stMetric"] { border: none !important; background: transparent !important; padding: 0.25rem 0 !important; }
[data-testid="stMetric"] label { font-size: 0.7rem !important; color: #666 !important; text-transform: uppercase !important; letter-spacing: 0.05em !important; }
[data-testid="stMetric"] .css-1wivap2 { font-size: 1.3rem !important; font-weight: 600 !important; color: #1a1a1a !important; font-family: inherit !important; }

/* Tighten expanders */
.stExpander { border: 1px solid #ddd !important; border-radius: 2px !important; }
.stExpander > details > summary { padding: 0.5rem 0.75rem !important; font-size: 0.85rem !important; }

/* Tighten alerts */
[data-testid="stAlert"] { border-radius: 2px !important; font-size: 0.85rem !important; padding: 0.5rem 0.75rem !important; }

/* Tighten file uploader */
[data-testid="stFileUploader"] { border: 1px dashed #bbb !important; border-radius: 2px !important; padding: 1rem !important; }

/* Reduce sidebar padding */
[data-testid="stSidebar"] .block-container { padding: 1rem 0.75rem !important; }
</style>
""")

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
    """Extract text from any uploaded file (PDF, TXT, DOCX, JSON, MD, HTML)"""
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
        
        elif file_ext in ['.html', '.htm']:
            text = f.getvalue().decode('utf-8', errors='replace')
            # Extract content from body tags only
            import re
            match = re.search(r'<body[^>]*>(.*?)</body>', text, re.DOTALL | re.IGNORECASE)
            if match:
                text = match.group(1)
            # Strip remaining HTML tags
            text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'<[^>]+>', ' ', text)
            # Clean up whitespace
            text = ' '.join(text.split())
            return text.strip()
        
        else:
            st.error(f"Unsupported file type: {file_ext}")
            return None
    
    except Exception as e:
        st.error(f"Cannot read {f.name}: {str(e)}")
        return None


def api_call(endpoint: str, method: str = "GET", data: dict = None, timeout: int = None) -> dict | None:
    """Make API call with authentication and error handling"""
    headers = {}
    if st.session_state.api_key:
        headers["Authorization"] = f"Bearer {st.session_state.api_key}"
    if st.session_state.session_id:
        headers["X-Session-ID"] = st.session_state.session_id
    
    url = f"{API_URL}{endpoint}"
    
    # Default timeouts
    if timeout is None:
        timeout = 30 if method == "GET" else 60
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=timeout)
        elif method == "POST":
            response = requests.post(url, json=data, headers=headers, timeout=timeout)
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
    left, center, right = st.columns([1, 2, 1])
    with center:
        st.markdown("#### Sign In")
        username = st.text_input("Username", value=st.session_state.get('username', ''))
        password = st.text_input("Password", type="password", value=st.session_state.get('password', ''))
        
        if st.button("Sign In", type="primary", use_container_width=True):
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
                        st.success(f"Welcome, {data.get('name', 'User')}!")
                        st.rerun()
                    else:
                        st.error("Invalid username or password.")
                except Exception as e:
                    st.error(f"Login failed: {str(e)}")
            else:
                st.error("Please enter both username and password.")
        
        st.markdown("---")
        st.caption("Demo accounts:")
        st.caption("admin / demo-admin-2024!")
        st.caption("staff / demo-staff-2024!")
        st.caption("user / demo-user-2024!")


def show_sidebar():
    """Show sidebar with tenant info, Documents menu, and navigation"""
    with st.sidebar:
        st.markdown("**NZ Legal Platform**")
        
        tenant_info = st.session_state.get('tenant_info', {})
        role = (tenant_info.get('role') or '').lower()
        
        # Navigation
        pages = ["Home", "Search", "Analysis", "Upload", "Similar Cases", "Element Check"]
        if role == 'admin':
            pages.append("Admin Panel")
        
        # Sync radio with current page
        current_page = st.session_state.get('current_page', 'Home')
        try:
            page_index = pages.index(current_page)
        except ValueError:
            page_index = 0
        
        page = st.radio("Navigation", pages, index=page_index, label_visibility="collapsed")
        
        # Update current page when radio changes
        if page != current_page:
            st.session_state.current_page = page
        
        st.markdown("---")
        
        # Upload buttons - clear mode selection
        if st.button("Upload (Temporary)", use_container_width=True, key="btn_upload_temp"):
            st.session_state.upload_mode = "temporary"
            st.session_state.current_page = "Upload"
            st.rerun()
        
        if role in ('admin', 'staff'):
            if st.button("Upload (Permanent)", use_container_width=True, key="btn_upload_perm"):
                st.session_state.upload_mode = "permanent"
                st.session_state.current_page = "Upload"
                st.rerun()
        
        st.markdown("---")
        
        # Tenant info display
        if tenant_info:
            st.caption(f"{tenant_info.get('name', 'User')} ({tenant_info.get('role', 'Unknown')})")
            
            if st.button("Sign Out", use_container_width=True):
                _do_logout()
                st.rerun()
        
        return page


def get_permanent_collections():
    """Fetch collections available for permanent upload."""
    result = api_call("/api/v1/collections")
    if not result or 'collections' not in result:
        return {"user_uploads": "User Uploaded Documents"}
    
    cols = {}
    for c in result['collections']:
        cid = c.get('id', '')
        # Skip temp sessions and confidential
        if cid.startswith('temp_session_') or cid == 'confidential':
            continue
        cols[cid] = c.get('description', cid)
    return cols


def show_upload():
    """Upload page with support for multiple files and folders"""
    st.title("Document Upload")
    
    # Get tenant role
    tenant_info = st.session_state.get('tenant_info', {})
    role = (tenant_info.get('role') or '').lower()
    
    # Determine mode from session state or default to temporary
    mode = st.session_state.get('upload_mode', 'temporary')
    is_temporary = mode == 'temporary'
    
    if is_temporary:
        st.caption("Temporary session upload — files cleared on sign out")
    else:
        st.caption("Permanent upload to knowledge base — admin & staff only")
    
    # Collection selector for permanent uploads
    target_collection = "temp_session" if is_temporary else "user_uploads"
    if not is_temporary and role in ('admin', 'staff'):
        perm_collections = get_permanent_collections()
        if perm_collections:
            col_options = list(perm_collections.keys())
            col_labels = {k: f"{v} ({perm_collections.get(k, k)})" for k, v in perm_collections.items()}
            selected = st.selectbox(
                "Target collection:",
                col_options,
                format_func=lambda x: col_labels.get(x, x),
                index=col_options.index("user_uploads") if "user_uploads" in col_options else 0,
                help="Choose which database collection to add these documents to."
            )
            target_collection = selected
    
    # Tabs for different upload methods
    tab1, tab2, tab3 = st.tabs(["Multiple Files", "ZIP Archive", "Supported Types"])
    
    with tab1:
        render_file_upload(role, is_temporary, target_collection)
    
    with tab2:
        render_zip_upload(role, is_temporary, target_collection)
    
    with tab3:
        render_supported_types()


def render_file_upload(role: str, is_temporary: bool = True, target_collection: str = "user_uploads"):
    """Render multiple file upload interface"""
    st.subheader("Upload Multiple Files")
    
    if is_temporary:
        st.info("Temporary files are only available for your current session.")
    else:
        st.success(f"Files will be stored permanently in the **{target_collection}** collection.")
    
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
        btn_label = "AI Ingest Files (Temporary)" if is_temporary else "AI Ingest Files (Permanent)"
        if st.button(btn_label, type="primary", key="upload_files_btn"):
            with st.spinner("Uploading and processing files..."):
                upload_files_to_api(uploaded_files, is_temporary, target_collection)


def render_zip_upload(role: str, is_temporary: bool = True, target_collection: str = "user_uploads"):
    """Render ZIP archive upload interface"""
    st.subheader("Upload Folder (ZIP Archive)")
    
    if not is_temporary:
        st.caption(f"ZIP contents will be added to the **{target_collection}** collection.")
    
    st.markdown("""
    Upload an entire folder by creating a ZIP archive:
    
    **Windows:** Right-click folder → "Send to" → "Compressed (zipped) folder" 
    **Mac:** Right-click folder → "Compress" 
    **Linux:** `zip -r my_folder.zip my_folder/`
    """)
    
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
                st.write(f"- {len(supported_files)} supported files will be processed")
                st.write(f"- {len(files) - len(supported_files)} items skipped (unsupported or folders)")
                
                with st.expander(f"View files ({len(supported_files)} supported)"):
                    for f in supported_files[:20]:
                        st.text(f)
                    if len(supported_files) > 20:
                        st.text(f"... and {len(supported_files) - 20} more")
        except zipfile.BadZipFile:
            st.error("Invalid ZIP file")
            return
        
        zip_file.seek(0)
        
        btn_label = "AI Ingest ZIP (Temporary)" if is_temporary else "AI Ingest ZIP (Permanent)"
        if st.button(btn_label, type="primary", key="upload_zip_btn"):
            with st.spinner("Extracting and processing files..."):
                upload_zip_to_api(zip_file, is_temporary, target_collection)


def render_supported_types():
    """Display supported file types"""
    st.subheader("Supported File Types")
    
    file_types = {
        "Documents": [
            (".pdf", "PDF documents", "Fully supported with page extraction"),
            (".docx", "Microsoft Word", "Modern Word format (.docx)"),
            (".doc", "Microsoft Word (Old)", "Legacy format (requires antiword)"),
            (".txt", "Plain Text", "UTF-8 encoded text files"),
            (".md", "Markdown", "Markdown formatted text"),
        ],
        "Spreadsheets": [
            (".xlsx", "Excel", "Modern Excel format (.xlsx)"),
            (".xls", "Excel (Old)", "Legacy Excel format"),
            (".csv", "CSV", "Comma-separated values"),
        ],
        "Web & Data": [
            (".html", "HTML", "Web pages"),
            (".htm", "HTML", "Web pages (alternate extension)"),
            (".json", "JSON", "JSON data files"),
        ],
    }
    
    for category, types in file_types.items():
        st.markdown(f"**{category}**")
        for ext, name, desc in types:
            st.markdown(f" - `{ext}` - {name}: {desc}")
        st.write("")
    
    st.markdown("""
    <div class="info-card">
        <strong>Upload Limits:</strong><br>
        Maximum 50 files per upload<br>
        Maximum 100 MB per ZIP archive<br>
        Files are chunked and embedded for semantic search
    </div>
    """, unsafe_allow_html=True)


def upload_files_to_api(files, is_temporary: bool, target_collection: str = "user_uploads"):
    """Upload multiple files to the API"""
    if not st.session_state.get("api_key"):
        st.error("Not authenticated")
        return
    
    headers = {"Authorization": f"Bearer {st.session_state.api_key}"}
    if st.session_state.get("session_id"):
        headers["X-Session-ID"] = st.session_state.session_id
    
    try:
        # Prepare files for upload
        upload_files = []
        for f in files:
            f.seek(0)
            mime = get_mime_type(f.name)
            upload_files.append(("files", (f.name, f.getvalue(), mime)))
        
        collection = f"temp_session_{st.session_state.session_id}" if is_temporary else target_collection
        data = {"collection": collection}
        
        response = requests.post(
            f"{API_URL}/api/v1/upload/files",
            headers=headers,
            files=upload_files,
            data=data,
            timeout=300
        )
        
        if response.status_code == 200:
            display_upload_result(response.json())
        else:
            st.error(f"Upload failed: {response.status_code}")
            try:
                st.error(response.json().get("detail", "Unknown error"))
            except:
                st.error(response.text[:500])
    
    except Exception as e:
        st.error(f"Error: {str(e)}")


def upload_zip_to_api(zip_file, is_temporary: bool, target_collection: str = "user_uploads"):
    """Upload ZIP archive to the API"""
    if not st.session_state.get("api_key"):
        st.error("Not authenticated")
        return
    
    headers = {"Authorization": f"Bearer {st.session_state.api_key}"}
    if st.session_state.get("session_id"):
        headers["X-Session-ID"] = st.session_state.session_id
    
    try:
        zip_file.seek(0)
        files = {"file": (zip_file.name, zip_file.getvalue(), "application/zip")}
        collection = f"temp_session_{st.session_state.session_id}" if is_temporary else target_collection
        data = {"collection": collection}
        
        response = requests.post(
            f"{API_URL}/api/v1/upload/zip",
            headers=headers,
            files=files,
            data=data,
            timeout=600
        )
        
        if response.status_code == 200:
            display_upload_result(response.json())
        else:
            st.error(f"Upload failed: {response.status_code}")
            try:
                st.error(response.json().get("detail", "Unknown error"))
            except:
                st.error(response.text[:500])
    
    except Exception as e:
        st.error(f"Error: {str(e)}")


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
        st.success(result['message'])
        
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
                        extra = f"Type: {detail.get('type', 'unknown')} | Words: {detail.get('words', 0)}"
                        if "pages" in detail:
                            extra += f" | Pages: {detail['pages']}"
                        if "sheets" in detail:
                            extra += f" | Sheets: {detail['sheets']}"
                        st.markdown(f"""
                        <div class="result-success">
                            <strong>{filename}</strong><br>
                            <span style="font-size:0.85rem; color:#475569;">{extra}</span>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div class="result-error">
                            <strong>{filename}</strong>: {detail.get('error', 'Unknown error')}
                        </div>
                        """, unsafe_allow_html=True)
    else:
        st.error(result.get('message', 'Upload failed'))


def show_home():
    """Home page with database statistics"""
    st.title("NZ Legal Platform")
    st.caption("Defence counsel legal research and analysis")
    
    stats = api_call("/health")
    if stats and isinstance(stats, dict) and 'database' in stats:
        db = stats['database']
        is_healthy = stats.get('status') == 'healthy'
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Documents", f"{db.get('total_documents', 0):,}")
        with col2:
            st.metric("Collections", len(db.get('collections', {})))
        with col3:
            st.metric("Status", "Online" if is_healthy else "Offline")
        
        st.markdown("---")
        
        # Flat collection list - no redundant expanders
        collections = db.get('collections', {})
        if collections:
            st.subheader("Collections")
            # Define category groupings with friendly names
            category_groups = {
                "Legislation": ['nz_legislation', 'nz_legislation_detailed'],
                "Case Law": ['nz_case_law', 'nzlii_criminal_cases', 'nz_criminal_cases'],
                "Police & Procedures": ['nz_police_manual', 'nz_police_procedures'],
                "General": ['nz_legal_unified', 'uncategorized'],
                "User Content": ['user_uploads', 'user_documents'],
            }
            
            for group_name, collection_names in category_groups.items():
                group_docs = 0
                for coll_name in collection_names:
                    if coll_name in collections:
                        coll_data = collections[coll_name]
                        if isinstance(coll_data, dict):
                            group_docs += coll_data.get('documents', coll_data.get('count', 0))
                        else:
                            group_docs += coll_data
                
                if group_docs > 0:
                    st.markdown(f"**{group_name}**: {group_docs:,} documents")
        else:
            st.info("No collection data available")
        
        # How To Guide
        st.markdown("---")
        st.subheader("How To Use This Platform")
        
        st.markdown("""
        <div style="background-color: #f0f4f8; border-left: 4px solid #3b5998; padding: 1rem; border-radius: 4px; margin-bottom: 1rem;">
            <p style="margin-bottom: 0.75rem; font-size: 0.9rem; line-height: 1.5;">
                Start by <strong>uploading the police disclosure document</strong>. When it's uploaded click <strong>AI Ingest</strong> so our AI can comprehend your upload. Now select <strong>Analysis</strong> from the menu. Type <code style="background: #e2e8f0; padding: 0.15rem 0.4rem; border-radius: 3px;">Analyse *document name*</code> with Analysis type <strong>General</strong>. Click <strong>Analyze</strong>. Very soon you'll have an overall perspective of the case (downloadable as PDF).
            </p>
            <p style="margin-bottom: 0.75rem; font-size: 0.9rem; line-height: 1.5;">
                Run through the Analysis types — <strong>Charge Review</strong> then <strong>Search Warrant</strong> followed by <strong>Evidence Review</strong>. Each response will detail the in-depth examination of the uploaded data — identifying flaws, errors, weaknesses &amp; linking precedents &amp; relevant Act references to take advantage of such.
            </p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.warning("Cannot fetch database stats. Check API connection.")


def get_result_title(item: dict) -> str:
    """Extract the best display title from search result metadata."""
    meta = item.get('metadata', {})
    for key in ['citation', 'case_name', 'title', 'source', 'act', 'section', 'act_year']:
        val = meta.get(key)
        if val and str(val).strip():
            if key in ('citation', 'case_name'):
                cat = meta.get('category', '')
                if cat:
                    return f"{val} [CATEGORY: {cat}]"
            return str(val)
    return 'Untitled Result'


def show_search():
    """Search page"""
    st.title("Search Legal Database")
    
    # Fetch available collections dynamically
    health = api_call("/health")
    available_collections = []
    collection_labels = {}
    if health and isinstance(health, dict) and 'database' in health:
        for name, info in health['database'].get('collections', {}).items():
            # Skip temp sessions and empty collections
            if name.startswith('temp_session_'):
                continue
            count = info.get('count', 0) if isinstance(info, dict) else info
            if count == 0:
                continue
            desc = info.get('description', name) if isinstance(info, dict) else name
            available_collections.append(name)
            collection_labels[name] = f"{desc} ({count})"
    
    # Fallback if API is down
    if not available_collections:
        available_collections = ["nz_legislation", "nz_case_law", "nzlii_criminal_cases", "nz_police_manual"]
        collection_labels = {c: c for c in available_collections}
    
    col1, col2 = st.columns([3,1])
    with col1:
        query = st.text_input("Enter search query:", placeholder="e.g., search warrant requirements")
    with col2:
        top_k = st.slider("Max results:", 3, 50, 10)
    
    col1, col2 = st.columns(2)
    with col1:
        # Use format_func to show friendly labels with counts
        collections = st.multiselect(
            "Filter collections:", 
            available_collections,
            default=available_collections[:2] if available_collections else [],
            format_func=lambda x: collection_labels.get(x, x)
        )
    with col2:
        st.caption("Leave empty for all collections")
    
    if st.button("Search", type="primary") and query.strip():
        with st.spinner("Searching database..."):
            result = api_call("/api/v1/search", "POST", {
                "query": query.strip(),
                "collections": collections if collections else None, 
                "top_k": top_k
            })
            if result and isinstance(result, dict):
                st.markdown(f"Found **{result.get('total', 0)}** results")
                results = result.get('results', [])
                if results:
                    col_a, col_b = st.columns(2)
                    for i, item in enumerate(results, 1):
                        target_col = col_a if i % 2 == 1 else col_b
                        with target_col:
                            title = get_result_title(item)
                            with st.expander(f"{i}. {title}"):
                                content = item.get('document', '')[:2000]
                                st.markdown(content + ("..." if len(item.get('document', '')) > 2000 else ""))
                                if 'metadata' in item:
                                    with st.expander("Metadata"):
                                        st.json(item['metadata'])
            else:
                st.error("No results or search failed")


def linkify_citations(text: str) -> str:
    """Convert NZ case citations in text to markdown links."""
    # Pattern: [YYYY] NZSC/NZCA/NZHC ### → NZLII link
    text = re.sub(
        r"(?<!\[)\[([0-9]{4})\]\s*(NZSC|NZCA|NZHC|NZDC|NZFc)\s*([0-9]+)(?!\]\()",
        r"[\1 \2 \3](https://www.nzlii.org/nz/cases/\2/\1/\3.html)",
        text,
        flags=re.IGNORECASE
    )
    # Pattern: R v Name [YYYY] NZCA ### → NZLII link
    text = re.sub(
        r"R\s+v\.?\s+([A-Za-z]+(?:\s+[A-Za-z]+)*)\s*\[([0-9]{4})\]\s*(NZSC|NZCA|NZHC|NZDC|NZFc)\s*([0-9]+)",
        r"[R v \1 [\2] \3 \4](https://www.nzlii.org/nz/cases/\3/\2/\4.html)",
        text,
        flags=re.IGNORECASE
    )
    return text


def _clean_for_pdf(text: str) -> str:
    """Strip markdown and HTML for clean PDF output."""
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)  # Remove markdown links
    text = re.sub(r'[#*_`]', '', text)  # Remove markdown formatting
    text = re.sub(r'⚠️\s*CITATION WARNING:.*?(?=\n\n|\Z)', '', text, flags=re.DOTALL)
    return text


def generate_analysis_pdf(result: dict) -> bytes:
    """Generate a PDF report from an analysis result using a Unicode font."""
    try:
        from fpdf import FPDF
    except ImportError:
        return b""

    pdf = FPDF()
    # Use system DejaVuSans font for full Unicode support (Māori macrons, etc.)
    pdf.add_font("DejaVu", "", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", uni=True)
    pdf.add_font("DejaVu", "B", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", uni=True)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Header
    pdf.set_font("DejaVu", "B", 16)
    pdf.cell(0, 10, "NZ Legal Platform — Analysis Report", ln=True, align="C")
    pdf.ln(2)
    pdf.set_draw_color(59, 89, 152)
    pdf.set_line_width(0.5)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)

    # Metadata
    pdf.set_font("DejaVu", "B", 11)
    pdf.cell(0, 8, f"Analysis Type: {result.get('analysis_type', 'general').replace('_', ' ').title()}", ln=True)
    pdf.set_font("DejaVu", "", 10)
    pdf.cell(0, 6, f"Date: {result.get('timestamp', '')}", ln=True)
    pdf.cell(0, 6, f"Confidence: {result.get('confidence', 0):.0%}", ln=True)
    pdf.ln(3)

    # Query
    pdf.set_font("DejaVu", "B", 11)
    pdf.cell(0, 8, "Question:", ln=True)
    pdf.set_font("DejaVu", "", 10)
    pdf.multi_cell(0, 6, _clean_for_pdf(result.get('query', '')))
    pdf.ln(3)

    # Answer
    pdf.set_font("DejaVu", "B", 11)
    pdf.cell(0, 8, "Analysis:", ln=True)
    pdf.set_font("DejaVu", "", 10)
    answer = _clean_for_pdf(result.get('answer', ''))
    pdf.multi_cell(0, 6, answer)
    pdf.ln(3)

    # Citations
    citations = result.get('citations', [])
    if citations:
        pdf.set_font("DejaVu", "B", 11)
        pdf.cell(0, 8, "Citations:", ln=True)
        pdf.set_font("DejaVu", "", 10)
        for c in citations:
            pdf.cell(5)
            pdf.cell(0, 6, f"• {c}", ln=True)
        pdf.ln(3)

    # Sources
    sources = result.get('sources', [])
    if sources:
        pdf.set_font("DejaVu", "B", 11)
        pdf.cell(0, 8, "Sources:", ln=True)
        pdf.set_font("DejaVu", "", 10)
        for s in sources:
            title = s.get('title', 'Unknown')
            cat = s.get('category', 'Unknown')
            rel = s.get('relevance', 0)
            pdf.cell(5)
            pdf.cell(0, 6, f"• {title} ({cat}, relevance: {rel:.1%})", ln=True)

    return bytes(pdf.output(dest="S"))


def show_analysis():
    """Legal analysis page"""
    st.title("Legal Analysis")
    
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        analysis_type = st.selectbox(
            "Analysis type:",
            ["general", "charge_review", "search_warrant", "evidence_review"]
        )
    with col2:
        st.markdown("""
        <div class="info-card" style="margin-top: 1.6rem;">
            Select a type and enter your question below.
        </div>
        """, unsafe_allow_html=True)
    with col3:
        deep_mode = st.toggle("Deep Analysis", value=False, help="Full multi-agent pipeline (~90s). Off = fast mode (~45s)")
    
    query = st.text_area(
        "Your question:", 
        placeholder="e.g., What are the requirements for a search warrant under the Search and Surveillance Act?",
        height=120
    )
    
    if st.button("Analyze", type="primary") and query.strip():
        with st.spinner("Analyzing... this may take 1–3 minutes for complex documents"):
            result = api_call("/api/v1/analyze", "POST", {
                "query": query.strip(),
                "analysis_type": analysis_type,
                "deep_analysis": deep_mode
            }, timeout=300)
            if result and 'answer' in result:
                # Header line: analysis type + question
                effective_type = result.get('analysis_type', analysis_type)
                st.markdown(f"**Analysis Conducted:** `{effective_type.replace('_', ' ').title()}`  ")
                st.markdown(f"**Question:** {result.get('query', query)}")
                st.markdown("---")

                # Executive summary from multi-agent pipeline
                if result.get('executive_summary'):
                    st.info(result['executive_summary'])

                # Download button row
                pdf_bytes = generate_analysis_pdf(result)
                col_dl1, col_dl2 = st.columns([1, 4])
                with col_dl1:
                    if pdf_bytes:
                        st.download_button(
                            label="Download PDF",
                            data=pdf_bytes,
                            file_name=f"legal_analysis_{effective_type}_{result.get('timestamp', 'report')[:10]}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                    else:
                        # Fallback to text if fpdf2 not installed
                        txt = f"Analysis Type: {effective_type}\n\n"
                        txt += f"Question: {result.get('query', query)}\n\n"
                        txt += f"Confidence: {result.get('confidence', 0):.0%}\n\n"
                        txt += "=" * 60 + "\n\n"
                        txt += result.get('answer', '')
                        st.download_button(
                            label="Download TXT",
                            data=txt.encode('utf-8'),
                            file_name=f"legal_analysis_{effective_type}.txt",
                            mime="text/plain",
                            use_container_width=True
                        )
                with col_dl2:
                    cap = f"Confidence: {result.get('confidence', 0):.0%}  •  {len(result.get('citations', []))} citations"
                    if result.get('confidence_breakdown'):
                        cap += f"  •  {result['confidence_breakdown'].split(chr(10))[0]}"
                    st.caption(cap)

                st.markdown("### Analysis Result")
                st.markdown(linkify_citations(result['answer']))

                # Strategic notes expander
                if result.get('strategic_notes'):
                    with st.expander("📋 Defence Strategy & Tactics"):
                        st.markdown(result['strategic_notes'])

                # Audit report warning
                if result.get('audit_report'):
                    if "⚠️" in result['audit_report'] or "Unverified" in result['audit_report']:
                        st.warning(result['audit_report'])
                    else:
                        with st.expander("✅ Citation Audit"):
                            st.markdown(result['audit_report'])

                # Confidence breakdown expander
                if result.get('confidence_breakdown'):
                    with st.expander("📊 Confidence Breakdown"):
                        st.markdown(result['confidence_breakdown'])

                # Agent debug trace panel (hidden by default)
                # To re-enable, uncomment the block below
                # if result.get('agent_trace'):
                #     with st.expander("🔬 Agent Debug Trace"):
                #         trace = result['agent_trace']
                #         if trace.get('pipeline'):
                #             pipe = trace['pipeline']
                #             st.markdown(f"**Pipeline:** {' → '.join(pipe.get('agents_used', []))}")
                #             st.markdown(f"**Total chunks retrieved:** {pipe.get('total_chunks_retrieved', 0)}")
                #             st.markdown(f"**Final confidence:** {pipe.get('final_confidence', 0):.0%}")
                #         with st.expander("📋 Raw JSON Trace"):
                #             st.json(trace)

            else:
                st.error("Analysis failed")


def show_similar_cases():
    """Similar cases page"""
    st.title("Similar Cases")
    st.markdown("Enter case facts to find similar precedents")
    
    facts = st.text_area(
        "Case facts:", 
        placeholder="e.g., Defendant was found with 5g of methamphetamine in vehicle during traffic stop...",
        height=150
    )
    
    if st.button("Find Similar Cases", type="primary") and facts.strip():
        with st.spinner("Finding similar cases..."):
            result = api_call("/api/v1/similar-cases", "POST", {"facts": facts.strip()})
            if result and 'results' in result:
                for i, case in enumerate(result['results'], 1):
                    with st.expander(f"Case {i}: {case.get('title', 'Untitled')}"):
                        st.markdown(case.get('summary', ''))
                        st.caption(case.get('citation', ''))
            else:
                st.info("No similar cases found")


def show_element_check():
    """Element check page"""
    st.title("Charge Element Check")
    st.markdown("Check if facts satisfy elements of an offense")
    
    col1, col2 = st.columns(2)
    with col1:
        offense = st.text_input("Offense name:", placeholder="e.g., Possession for Supply (Misuse of Drugs Act)")
    with col2:
        st.markdown("""
        <div class="info-card" style="margin-top: 1.6rem;">
            Enter the offense and facts below to begin.
        </div>
        """, unsafe_allow_html=True)
    
    facts = st.text_area("Facts of case:", height=150)
    
    if st.button("Check Elements", type="primary") and offense.strip() and facts.strip():
        with st.spinner("Checking elements..."):
            result = api_call("/api/v1/check-elements", "POST", {
                "offense": offense.strip(),
                "facts": facts.strip()
            })
            if result and 'elements' in result:
                st.markdown("### Element Analysis")
                for elem in result['elements']:
                    status = elem.get('status', '').lower()
                    if 'satisfied' in status or 'met' in status or 'proven' in status:
                        st.markdown(f"""
                        <div class="result-success">
                            <strong>{elem.get('element', '')}</strong><br>
                            <span style="font-size:0.85rem; color:#475569;">{elem.get('reasoning', '')}</span>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div class="result-error">
                            <strong>{elem.get('element', '')}</strong><br>
                            <span style="font-size:0.85rem; color:#475569;">{elem.get('reasoning', '')}</span>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.error("Element check failed")


def show_usage():
    """Usage analytics page"""
    st.title("Usage Analytics")
    
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
    st.title("Admin Panel")
    
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
        login()
        return
    
    page = show_sidebar()
    
    # Sync current page from radio selection
    st.session_state.current_page = page
    
    if page == "Home":
        show_home()
    elif page == "Search":
        show_search()
    elif page == "Analysis":
        show_analysis()
    elif page == "Upload":
        show_upload()
    elif page == "Similar Cases":
        show_similar_cases()
    elif page == "Element Check":
        show_element_check()
    elif page == "Admin Panel":
        show_admin_panel()


if __name__ == "__main__":
    main()
