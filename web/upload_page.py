#!/usr/bin/env python3
"""
Document Upload Page for NZ Legal Platform
Supports multiple files, folders (via zip), and various file types
"""

import streamlit as st
import requests
import os
import zipfile
import io
from typing import List, Dict, Any

API_URL = os.getenv("API_URL", "http://localhost:8000")

# Supported file types
SUPPORTED_EXTENSIONS = [
    '.txt', '.pdf', '.doc', '.docx', '.xlsx', '.xls', 
    '.html', '.htm', '.md', '.csv', '.json'
]


def upload_page():
    """Render the document upload page"""
    st.title("📁 Document Upload")
    st.markdown("Upload legal documents to the knowledge base")
    
    # Tabs for different upload methods
    tab1, tab2, tab3 = st.tabs(["📄 Multiple Files", "📦 ZIP Archive", "ℹ️ Supported Types"])
    
    with tab1:
        render_multiple_file_upload()
    
    with tab2:
        render_zip_upload()
    
    with tab3:
        render_supported_types()


def render_multiple_file_upload():
    """Render multiple file upload interface"""
    st.subheader("Upload Multiple Files")
    
    # Collection selection
    collection = st.selectbox(
        "Target Collection",
        ["user_uploads", "Temporary Session Storage"],
        key="upload_collection_select"
    )
    
    is_temporary = collection == "Temporary Session Storage"
    
    if is_temporary:
        st.info("📌 Temporary files are only available for your current session and will be deleted when you log out.")
        if "session_id" not in st.session_state:
            import uuid
            st.session_state.session_id = str(uuid.uuid4())
    
    # File uploader with multiple files support
    uploaded_files = st.file_uploader(
        "Choose files to upload",
        type=[ext.replace('.', '') for ext in SUPPORTED_EXTENSIONS],
        accept_multiple_files=True,
        key="multi_file_uploader",
        help="Select multiple files. Supported: PDF, DOC, DOCX, TXT, XLSX, HTML, MD, CSV, JSON"
    )
    
    if uploaded_files:
        st.write(f"**{len(uploaded_files)} file(s) selected:**")
        
        # Show file info
        cols = st.columns([3, 1, 1])
        cols[0].markdown("**Filename**")
        cols[1].markdown("**Type**")
        cols[2].markdown("**Size**")
        
        total_size = 0
        for file in uploaded_files:
            cols = st.columns([3, 1, 1])
            cols[0].write(file.name)
            cols[1].code(file.type or "unknown")
            size_kb = len(file.getvalue()) / 1024
            total_size += size_kb
            cols[2].write(f"{size_kb:.1f} KB")
        
        st.write(f"**Total size:** {total_size:.1f} KB ({total_size/1024:.2f} MB)")
        
        # Upload button
        if st.button("🚀 Upload Files", type="primary", key="upload_files_btn"):
            with st.spinner("Uploading and processing files..."):
                upload_multiple_files(uploaded_files, collection, is_temporary)


def render_zip_upload():
    """Render ZIP archive upload interface"""
    st.subheader("Upload Folder (ZIP Archive)")
    
    st.markdown("""
    Upload an entire folder by creating a ZIP archive:
    
    **Windows:**
    1. Right-click the folder
    2. Select "Send to" → "Compressed (zipped) folder"
    
    **Mac:**
    1. Right-click the folder
    2. Select "Compress"
    
    **Linux:**
    ```bash
    zip -r my_folder.zip my_folder/
    ```
    """)
    
    # Collection selection
    collection = st.selectbox(
        "Target Collection",
        ["user_uploads", "Temporary Session Storage"],
        key="zip_collection_select"
    )
    
    is_temporary = collection == "Temporary Session Storage"
    
    if is_temporary and "session_id" not in st.session_state:
        import uuid
        st.session_state.session_id = str(uuid.uuid4())
    
    # ZIP file uploader
    zip_file = st.file_uploader(
        "Choose ZIP archive",
        type=["zip"],
        key="zip_uploader"
    )
    
    if zip_file:
        # Preview ZIP contents
        try:
            with zipfile.ZipFile(io.BytesIO(zip_file.getvalue())) as zf:
                files = [f for f in zf.namelist() if not f.endswith('/')]
                supported_files = [f for f in files if any(f.lower().endswith(ext) for ext in SUPPORTED_EXTENSIONS)]
                
                st.write(f"**Archive contains {len(files)} items:**")
                st.write(f"- ✅ {len(supported_files)} supported files will be processed")
                st.write(f"- ⚠️ {len(files) - len(supported_files)} items skipped (unsupported or folders)")
                
                # Show first 10 files
                with st.expander(f"View files ({len(supported_files)} supported)"):
                    for f in supported_files[:10]:
                        st.text(f)
                    if len(supported_files) > 10:
                        st.text(f"... and {len(supported_files) - 10} more")
        
        except zipfile.BadZipFile:
            st.error("❌ Invalid ZIP file")
            return
        
        # Reset file pointer
        zip_file.seek(0)
        
        # Upload button
        if st.button("🚀 Upload ZIP Archive", type="primary", key="upload_zip_btn"):
            with st.spinner("Extracting and processing files..."):
                upload_zip_file(zip_file, collection, is_temporary)


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
        "🌐 Web": [
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
    **Notes:**
    - Maximum 50 files per upload
    - Maximum 100 MB per ZIP archive
    - Files are chunked and embedded for semantic search
    - Supported files in ZIP are automatically extracted and processed
    """)


def upload_multiple_files(files: List[Any], collection: str, is_temporary: bool):
    """Upload multiple files to the API"""
    if not st.session_state.get("api_key"):
        st.error("❌ Not authenticated")
        return
    
    headers = {"Authorization": f"Bearer {st.session_state.api_key}"}
    
    if is_temporary:
        headers["X-Session-ID"] = st.session_state.session_id
    
    try:
        # Prepare files for upload
        upload_files = []
        for file in files:
            file.seek(0)
            upload_files.append(("files", (file.name, file.getvalue(), file.type or "application/octet-stream")))
        
        # Prepare data
        data = {"collection": "temp_session" if is_temporary else collection}
        
        # Send request
        response = requests.post(
            f"{API_URL}/api/v1/upload/files",
            headers=headers,
            files=upload_files,
            data=data,
            timeout=120
        )
        
        if response.status_code == 200:
            result = response.json()
            display_upload_result(result)
        else:
            st.error(f"❌ Upload failed: {response.status_code}")
            try:
                detail = response.json().get("detail", "Unknown error")
                st.error(detail)
            except:
                st.error(response.text[:500])
    
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")


def upload_zip_file(zip_file: Any, collection: str, is_temporary: bool):
    """Upload ZIP archive to the API"""
    if not st.session_state.get("api_key"):
        st.error("❌ Not authenticated")
        return
    
    headers = {"Authorization": f"Bearer {st.session_state.api_key}"}
    
    if is_temporary:
        headers["X-Session-ID"] = st.session_state.session_id
    
    try:
        zip_file.seek(0)
        files = {"file": (zip_file.name, zip_file.getvalue(), "application/zip")}
        data = {"collection": "temp_session" if is_temporary else collection}
        
        response = requests.post(
            f"{API_URL}/api/v1/upload/zip",
            headers=headers,
            files=files,
            data=data,
            timeout=180
        )
        
        if response.status_code == 200:
            result = response.json()
            display_upload_result(result)
        else:
            st.error(f"❌ Upload failed: {response.status_code}")
            try:
                detail = response.json().get("detail", "Unknown error")
                st.error(detail)
            except:
                st.error(response.text[:500])
    
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")


def display_upload_result(result: Dict[str, Any]):
    """Display upload result"""
    if result.get("success"):
        st.success(f"✅ {result['message']}")
        
        # Summary metrics
        col1, col2, col3 = st.columns(3)
        col1.metric("Files Processed", result.get("files_processed", 0))
        col2.metric("Files Failed", result.get("files_failed", 0))
        col3.metric("Total Chunks", result.get("total_chunks", 0))
        
        # Details table
        if result.get("details"):
            with st.expander("View Details"):
                for detail in result["details"]:
                    status = detail.get("status", "unknown")
                    filename = detail.get("filename", "unknown")
                    
                    if status == "success":
                        st.success(f"✅ {filename}")
                        cols = st.columns(3)
                        if "words" in detail:
                            cols[0].write(f"Words: {detail['words']}")
                        if "pages" in detail:
                            cols[1].write(f"Pages: {detail['pages']}")
                        if "type" in detail:
                            cols[2].write(f"Type: {detail['type']}")
                    else:
                        st.error(f"❌ {filename}: {detail.get('error', 'Unknown error')}")
    else:
        st.error(f"❌ {result.get('message', 'Upload failed')}")
        # Show detailed error info for each failed file
        if result.get("details"):
            with st.expander("View Error Details"):
                for detail in result["details"]:
                    if detail.get("status") == "failed" or "error" in detail:
                        st.error(f"📄 **{detail.get('filename', 'Unknown file')}**: {detail.get('error', 'Unknown error')}")


if __name__ == "__main__":
    upload_page()
