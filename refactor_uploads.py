#!/usr/bin/env python3
"""
Refactor upload forms:
- Sidebar/column → permanent DB only
- Main page → ephemeral/temporary only
"""

with open('web/streamlit_app.py', 'r') as f:
    content = f.read()

# 1. Remove temporary upload from sidebar, keep permanent only
old_sidebar_temp = '''            # Session temporary - All users
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
            
            if role == 'user':'''
new_sidebar_temp = '''            if role == 'user':'''
content = content.replace(old_sidebar_temp, new_sidebar_temp)

# 2. render_file_upload → ephemeral only
old_file_upload = '''def render_file_upload(role: str):
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
                upload_files_to_api(uploaded_files, is_temporary)'''

new_file_upload = '''def render_file_upload(role: str):
    """Render multiple file upload interface (ephemeral only)"""
    st.subheader("Upload Multiple Files")
    
    st.info("📌 Temporary files are only available for your current session and will be deleted when you log out.")
    if "session_id" not in st.session_state:
        import uuid
        st.session_state.session_id = str(uuid.uuid4())
    
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
                upload_files_to_api(uploaded_files)'''
content = content.replace(old_file_upload, new_file_upload)

# 3. render_zip_upload → ephemeral only
old_zip_upload = '''def render_zip_upload(role: str):
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
                upload_zip_to_api(zip_file, is_temporary)'''

new_zip_upload = '''def render_zip_upload(role: str):
    """Render ZIP archive upload interface (ephemeral only)"""
    st.subheader("Upload Folder (ZIP Archive)")
    
    st.markdown("""
    Upload an entire folder by creating a ZIP archive:
    
    **Windows:** Right-click folder → "Send to" → "Compressed (zipped) folder"  
    **Mac:** Right-click folder → "Compress"  
    **Linux:** `zip -r my_folder.zip my_folder/`
    """)
    
    st.info("📌 Temporary files are only available for your current session and will be deleted when you log out.")
    if "session_id" not in st.session_state:
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
                upload_zip_to_api(zip_file)'''
content = content.replace(old_zip_upload, new_zip_upload)

# 4. upload_files_to_api → temp only + X-Session-ID
old_files_api = '''def upload_files_to_api(files, is_temporary: bool):
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
        st.error(f"❌ Error: {str(e)}")'''

new_files_api = '''def upload_files_to_api(files):
    """Upload multiple files to the API (ephemeral/temporary only)"""
    if not st.session_state.get("api_key"):
        st.error("❌ Not authenticated")
        return
    
    headers = {"Authorization": f"Bearer {st.session_state.api_key}"}
    
    # Session ID for temporary collection
    if "session_id" not in st.session_state:
        import uuid
        st.session_state.session_id = str(uuid.uuid4())
    headers["X-Session-ID"] = st.session_state.session_id
    
    try:
        # Prepare files for upload
        upload_files = []
        for f in files:
            f.seek(0)
            mime = get_mime_type(f.name)
            upload_files.append(("files", (f.name, f.getvalue(), mime)))
        
        data = {"collection": "temp_session"}
        
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
        st.error(f"❌ Error: {str(e)}")'''
content = content.replace(old_files_api, new_files_api)

# 5. upload_zip_to_api → temp only + X-Session-ID
old_zip_api = '''def upload_zip_to_api(zip_file, is_temporary: bool):
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
        st.error(f"❌ Error: {str(e)}")'''

new_zip_api = '''def upload_zip_to_api(zip_file):
    """Upload ZIP archive to the API (ephemeral/temporary only)"""
    if not st.session_state.get("api_key"):
        st.error("❌ Not authenticated")
        return
    
    headers = {"Authorization": f"Bearer {st.session_state.api_key}"}
    
    # Session ID for temporary collection
    if "session_id" not in st.session_state:
        import uuid
        st.session_state.session_id = str(uuid.uuid4())
    headers["X-Session-ID"] = st.session_state.session_id
    
    try:
        zip_file.seek(0)
        files = {"file": (zip_file.name, zip_file.getvalue(), "application/zip")}
        data = {"collection": "temp_session"}
        
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
        st.error(f"❌ Error: {str(e)}")'''
content = content.replace(old_zip_api, new_zip_api)

with open('web/streamlit_app.py', 'w') as f:
    f.write(content)

print("✅ Upload refactoring applied")
