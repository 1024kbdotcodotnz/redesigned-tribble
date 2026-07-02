#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AEGIS ⚖️ - NZ's Legal Assistant (Streamlit Frontend)
FIXED v4: Upload button styling, auto-redirect, multi-file upload, timer, expert analysis, print button
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any

import requests
import streamlit as st

from dotenv import load_dotenv

# Load .env from the project root so the frontend always uses the same
# environment as the API, regardless of the working directory it was started from.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# AEGIS report export helpers
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.report_export import (
    build_disclosure_docx,
    build_disclosure_pdf,
    build_docx,
    build_pdf,
)

st.set_page_config(
    page_title="AEGIS ⚖️ - NZ's Legal Assistant",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
CHROMADB_PATH = os.getenv("CHROMADB_PATH", "/workspace/chroma_db_fresh")


def load_css(filename: str = "theme.css") -> None:
    css_path = Path(__file__).resolve().with_name(filename)
    if css_path.exists():
        css = css_path.read_text(encoding="utf-8")
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


load_css("theme.css")


# ─── Session State ──────────────────────────────────────────────────────


def init_session() -> None:
    defaults = {
        "apikey": None,
        "sessionid": str(uuid.uuid4()),
        "tenantinfo": {},
        "page": "Search",
        "uploadeddocuments": [],
        "demoemail": "",
        "demophone": "",
        "challengeid": "",
        "democodesent": False,
        "accesscode": "",
        "authmode": None,
        "role": None,
        "tenantid": None,
        "displayname": None,
        "staffusername": "",
        "authenticated": False,
        "lastuploadcollection": None,
        "uploadcomplete": False,
        "disclosure_text": "",
        "disclosure_file_content": None,
        "disclosure_processed_files": [],
        "analysis_failed": False,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def reset_auth_state() -> None:
    for key in [
        "apikey",
        "tenantinfo",
        "challengeid",
        "democodesent",
        "uploadeddocuments",
        "accesscode",
        "authmode",
        "role",
        "tenantid",
        "displayname",
        "demoemail",
        "demophone",
        "staffusername",
        "authenticated",
        "lastuploadcollection",
        "uploadcomplete",
        "disclosure_text",
        "disclosure_file_content",
        "disclosure_processed_files",
    ]:
        st.session_state.pop(key, None)
    init_session()
    st.session_state["sessionid"] = str(uuid.uuid4())
    st.session_state["page"] = "Home"


# ─── API Client ─────────────────────────────────────────────────────────


def api_call(
    endpoint: str,
    data: dict | None = None,
    method: str = "POST",
    apikey: str | None = None,
    sessionid: str | None = None,
    files: list | None = None,
    filefieldname: str = "files",
    quiet: bool = False,
    connecttimeout: int = 15,
    readtimeout: int = 60,
) -> Any:
    from urllib.parse import urljoin

    base = API_URL if API_URL.endswith("/") else API_URL + "/"
    url = urljoin(base, endpoint.lstrip("/"))
    headers: dict[str, str] = {}

    # FIXED: Always use the stored sessionid; fall back to current one.
    # The server needs X-Session-ID to route temp uploads correctly.
    effective_apikey = apikey or st.session_state.get("apikey")
    effective_sessionid = sessionid or st.session_state.get("sessionid")

    if effective_apikey:
        headers["Authorization"] = f"Bearer {effective_apikey}"
    if effective_sessionid:
        headers["X-Session-ID"] = effective_sessionid

    try:
        if files:
            multipartfiles = []
            for fileobj in files:
                mime = getattr(fileobj, "type", None) or "application/octet-stream"
                multipartfiles.append(
                    (filefieldname, (fileobj.name, fileobj.getvalue(), mime))
                )

            formdata = {}
            if isinstance(data, dict):
                for key, value in data.items():
                    if value is not None:
                        formdata[key] = str(value)

            response = requests.request(
                method.upper(),
                url,
                headers=headers,
                data=formdata,
                files=multipartfiles,
                timeout=(connecttimeout, readtimeout),
            )
        else:
            if method.upper() == "GET":
                response = requests.get(
                    url,
                    headers=headers,
                    params=data,
                    timeout=(connecttimeout, readtimeout),
                )
            else:
                response = requests.request(
                    method.upper(),
                    url,
                    headers=headers,
                    json=data,
                    timeout=(connecttimeout, readtimeout),
                )

        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            return response.json()
        return {"text": response.text, "statuscode": response.status_code}

    except requests.HTTPError as exc:
        detail = None
        try:
            detail = response.json()
        except Exception:
            detail = response.text if "response" in locals() else str(exc)
        error_msg = f"API error: {exc} - {detail}"
        st.session_state["last_api_error"] = error_msg
        if not quiet:
            st.error(error_msg)
        return None
    except Exception as exc:
        error_msg = f"API error: {exc}"
        st.session_state["last_api_error"] = error_msg
        if not quiet:
            st.error(error_msg)
        return None


def api_call_raw(
    endpoint: str,
    method: str = "GET",
    data: dict | None = None,
    apikey: str | None = None,
    sessionid: str | None = None,
    connecttimeout: int = 15,
    readtimeout: int = 60,
) -> bytes | str:
    """Return raw response bytes for binary endpoints, or an error string."""
    from urllib.parse import urljoin

    base = API_URL if API_URL.endswith("/") else API_URL + "/"
    url = urljoin(base, endpoint.lstrip("/"))
    headers: dict[str, str] = {}

    effective_apikey = apikey or st.session_state.get("apikey")
    effective_sessionid = sessionid or st.session_state.get("sessionid")

    if effective_apikey:
        headers["Authorization"] = f"Bearer {effective_apikey}"
    if effective_sessionid:
        headers["X-Session-ID"] = effective_sessionid

    try:
        if method.upper() == "GET":
            response = requests.get(
                url,
                headers=headers,
                params=data,
                timeout=(connecttimeout, readtimeout),
            )
        else:
            response = requests.request(
                method.upper(),
                url,
                headers=headers,
                json=data,
                timeout=(connecttimeout, readtimeout),
            )
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        return str(e)


# ─── UI Components ──────────────────────────────────────────────────────


def render_brand_header() -> None:
    st.markdown(
        """
        <div class="aegis-shell">
          <div class="aegis-brand">
            <div>
              <div class="aegis-kicker">NZ's Legal Assistant</div>
              <h1 class="aegis-title"><span>AEGIS ⚖️</span></h1>
              <p class="aegis-subtitle">Secure Legal Research</p>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def run_with_timer(message: str, fn):
    loaderslot = st.empty()
    try:
        with loaderslot.container():
            with st.spinner(message, show_time=True):
                return fn()
    finally:
        loaderslot.empty()


# ─── Auth ───────────────────────────────────────────────────────────────


def login() -> None:
    render_brand_header()
    clienttab, stafftab = st.tabs(["Client Access", "Staff / Admin"])

    with clienttab:
        st.markdown("<div class='aegis-panel'>", unsafe_allow_html=True)
        st.markdown("### Secure Client Access")
        st.markdown(
            "<div class='aegis-note'>Anonymous one-click secure access to analysis tools.</div>",
            unsafe_allow_html=True,
        )

        st.markdown("#### Welcome to AEGIS ⚖️ NZ's Legal Advisor")
        st.markdown(
            "Click below to start a secure, anonymous demo session. No credentials required. Your visit is ephemeral, we retain no data. All uploads, input & output are destroyed on log off."
        )

        if st.button(
            "⚡ Start Session",
            type="primary",
            use_container_width=True,
            key="quickdemo",
        ):
            with st.spinner("Starting secure session..."):
                result = api_call(
                    "/auth/login",
                    data={"email": "demo@aegis.nz", "password": "demo"},
                    sessionid=st.session_state["sessionid"],
                )
                if result and result.get("access_token"):
                    st.session_state["authenticated"] = True
                    st.session_state["authmode"] = "client"
                    st.session_state["role"] = result.get("role", "user")
                    st.session_state["tenantid"] = result.get("tenant_id")
                    st.session_state["displayname"] = "Demo User"
                    st.session_state["apikey"] = result.get("access_token")
                    st.session_state["tenantinfo"] = {
                        "tenant_id": result.get("tenant_id"),
                        "role": result.get("role"),
                        "expires_at": result.get("expires_at"),
                    }
                    st.success("✓ Session started")
                    st.rerun()
                else:
                    st.error("Session failed. Please try again.")

    with stafftab:
        st.markdown("<div class='aegis-panel'>", unsafe_allow_html=True)
        st.markdown("### Staff / Admin Login")
        st.markdown(
            "<div class='aegis-note'>Use your staff or admin credentials to access privileged features.</div>",
            unsafe_allow_html=True,
        )

        staffusername = st.text_input(
            "Username",
            value=st.session_state.get("staffusername", ""),
            key="staffloginusername",
        )
        staffpassword = st.text_input(
            "Password", type="password", key="staffloginpassword"
        )

        if st.button(
            "Sign In", type="primary", use_container_width=True, key="staffloginbutton"
        ):
            if not staffusername.strip() or not staffpassword.strip():
                st.warning("Username and password are required.")
            else:
                result = api_call(
                    "/auth/staff/login",
                    data={"username": staffusername.strip(), "password": staffpassword},
                    sessionid=st.session_state["sessionid"],
                )
                if result:
                    role = str(result.get("role", "staff")).strip().lower()
                    displayname = result.get("name") or staffusername.strip()
                    st.session_state["authenticated"] = True
                    st.session_state["authmode"] = "staff"
                    st.session_state["staffusername"] = staffusername.strip()
                    st.session_state["role"] = role
                    st.session_state["tenantid"] = result.get("tenant_id")
                    st.session_state["displayname"] = displayname
                    st.session_state["apikey"] = result.get("access_token") or result.get("api_key")
                    st.session_state["tenantinfo"] = {
                        "tenant_id": result.get("tenant_id"),
                        "role": role,
                        "display_name": displayname,
                        "quotas": result.get("quotas"),
                    }
                    st.success(f"Signed in as {displayname}.")
                    st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)


# ─── Sidebar ────────────────────────────────────────────────────────────


def show_sidebar() -> str:
    with st.sidebar:
        st.markdown("## AEGIS ⚖️")
        st.caption("NZ's Legal Assistant")

        role = str(st.session_state.get("role", "user")).lower().strip() or "user"
        displayname = (
            st.session_state.get("displayname")
            or st.session_state.get("demoemail")
            or st.session_state.get("staffusername")
            or "Authenticated user"
        )
        st.info(f"Signed in as {displayname}")
        st.caption(f"Role: {role}")

        if role == "admin":
            pages = [
                "Search",
                "Upload",
                "Defence Analysis",
                "Collection Manager",
                "Collection Inspector",
                "Admin Panel",
                "Email Inbox",
            ]
        elif role in ["staff", "adminstaff"]:
            pages = [
                "Search",
                "Upload",
                "Defence Analysis",
                "Collection Manager",
                "Collection Inspector",
                "Email Inbox",
            ]
        else:
            pages = ["Search", "Defence Analysis"]

        current = st.session_state.get("page", "Home")
        if current not in pages:
            current = pages[0]

        page = st.radio(
            "Navigate",
            pages,
            index=pages.index(current),
            label_visibility="collapsed",
            key="navradio",
        )
        st.session_state["page"] = page

        if st.button("Log Out", use_container_width=True, key="logoutbtn"):
            currentapikey = st.session_state.get("apikey")
            currentsessionid = st.session_state.get("sessionid")
            authmode = st.session_state.get("authmode")
            if currentapikey and currentsessionid:
                if authmode == "client":
                    api_call(
                        "/auth/demo/logout",
                        method="POST",
                        apikey=currentapikey,
                        sessionid=currentsessionid,
                        quiet=True,
                    )
                    api_call(
                        "/api/v1/ingest/clear-session",
                        method="POST",
                        apikey=currentapikey,
                        sessionid=currentsessionid,
                        quiet=True,
                    )
            reset_auth_state()
            st.rerun()

        return page


# ─── Collection Helpers ─────────────────────────────────────────────────


def get_existing_collections() -> list[str]:
    """FIXED: Use API first, fall back to direct Chroma."""
    result = api_call(
        "/api/v1/collections", method="GET", apikey=st.session_state.get("apikey")
    )
    if result and isinstance(result, dict) and "collections" in result:
        return sorted(
            [c.get("id", "") for c in result["collections"] if c.get("id")],
            key=str.lower,
        )
    # Fallback to direct Chroma if API fails or user is not yet authed
    try:
        import chromadb

        client = chromadb.PersistentClient(path=CHROMADB_PATH)
        collections = client.list_collections()
        names = []
        for collection in collections:
            name = getattr(collection, "name", None)
            if name:
                names.append(name)
            else:
                names.append(str(collection))
        return sorted(set(names), key=str.lower)
    except Exception as exc:
        st.warning(f"Could not load existing collections: {exc}")
        return []


# ─── Pages ──────────────────────────────────────────────────────────────


def show_home() -> None:
    render_brand_header()
    st.markdown("<div class='aegis-panel'>", unsafe_allow_html=True)
    st.markdown("### Home")
    st.write(
        "Upload documents, search indexed material, and run analysis against your legal corpus."
    )
    st.markdown("</div>", unsafe_allow_html=True)


def show_upload() -> None:
    render_brand_header()
    st.markdown("<div class='aegis-panel'>", unsafe_allow_html=True)

    st.markdown("### Permanent Upload")
    st.markdown(
        "<div class='aegis-note'>Upload documents into the permanent Chroma database. "
        "Create a new collection or append to an existing one. Temporary session uploads are handled from Defence Analysis.</div>",
        unsafe_allow_html=True,
    )

    collectionmode = st.radio(
        "Collection action",
        ["Create new collection", "Add to existing collection"],
        horizontal=True,
        key="collectionmode",
    )

    if collectionmode == "Create new collection":
        collectionname = st.text_input(
            "New collection name",
            value=st.session_state.get("newcollectionname", ""),
            key="newcollectionname",
            placeholder="e.g. police-disclosure-june-2026",
        ).strip()
    else:
        existingcollections = [
            c for c in get_existing_collections()
            if "temp" not in c.lower()
        ]
        if existingcollections:
            collectionname = st.selectbox(
                "Existing collection",
                options=existingcollections,
                key="existingcollectionselect",
            )
        else:
            collectionname = st.text_input(
                "Existing collection name",
                value=st.session_state.get("existingcollectionname", ""),
                key="existingcollectionname",
                placeholder="Enter the target collection name",
            ).strip()
            st.warning("No existing collections found in Chroma.")

    uploadedfiles = st.file_uploader(
        "Select one or more files",
        accept_multiple_files=True,
        type=["txt", "pdf", "docx", "md", "json", "zip"],
        key="uploadfileswidget",
    )

    if uploadedfiles:
        file_list_html = "".join(f"<li>{file.name}</li>" for file in uploadedfiles)
        st.markdown(
            f"<div class='aegis-list'><strong>Selected files</strong><ul>{file_list_html}</ul></div>",
            unsafe_allow_html=True,
        )

    # ─── FIXED: Upload button states ────────────────────────────────────────
    # The file uploader's internal "Upload" button is styled RED in theme.css
    # Our action button changes based on state:
    #   - No files selected: grey disabled
    #   - Files selected but not uploaded: green "Ingest Files"
    #   - Upload complete: green "Ingest Files" (already done)

    upload_complete = st.session_state.get("uploadcomplete", False)
    has_files = bool(uploadedfiles)

    # Inject dynamic button styling
    button_label = "✓ Ingest Files" if upload_complete else "📤 Ingest Files"
    button_disabled = not has_files

    # We use a container to inject CSS that targets this specific button
    button_container = st.container()
    with button_container:
        if button_disabled:
            # Grey disabled state
            st.markdown(
                """
            <style>
            div[data-testid="stVerticalBlock"]:has(> div > div > div > div > button[key="btningestfiles"]) button {
                background-color: #666666 !important;
                border-color: #666666 !important;
                color: #cccccc !important;
                cursor: not-allowed !important;
                opacity: 0.8 !important;
            }
            </style>
            """,
                unsafe_allow_html=True,
            )
        else:
            # Green active state
            st.markdown(
                """
            <style>
            div[data-testid="stVerticalBlock"]:has(> div > div > div > div > button[key="btningestfiles"]) button {
                background-color: #28a745 !important;
                border-color: #28a745 !important;
                color: white !important;
            }
            div[data-testid="stVerticalBlock"]:has(> div > div > div > div > button[key="btningestfiles"]) button:hover {
                background-color: #218838 !important;
                border-color: #1e7e34 !important;
            }
            </style>
            """,
                unsafe_allow_html=True,
            )

        ingest_btn = st.button(
            button_label,
            type="primary",
            use_container_width=True,
            key="btningestfiles",
            disabled=button_disabled,
        )

    if ingest_btn and has_files:
        if not collectionname:
            st.warning("Enter a collection name.")
            st.markdown("</div>", unsafe_allow_html=True)
            return

        targetcollection = collectionname

        with st.spinner("Uploading and indexing for search and analysis..."):
            # FIXED: Correct file field names matching server endpoints
            if len(uploadedfiles) == 1 and uploadedfiles[0].name.lower().endswith(
                ".zip"
            ):
                result = api_call(
                    "/api/v1/upload/zip",
                    data={"collection": targetcollection},
                    method="POST",
                    apikey=st.session_state.get("apikey"),
                    sessionid=st.session_state.get("sessionid"),
                    files=uploadedfiles,
                    filefieldname="file",
                    # Server: UploadFile = File(..., alias="file")
                )
            else:
                result = api_call(
                    "/api/v1/upload/files",
                    data={"collection": targetcollection},
                    method="POST",
                    apikey=st.session_state.get("apikey"),
                    sessionid=st.session_state.get("sessionid"),
                    files=uploadedfiles,
                    filefieldname="files",
                    # Server: List[UploadFile] = File(..., alias="files")
                )

        if result:
            st.session_state["uploadeddocuments"] = (
                st.session_state.get("uploadeddocuments", []) + [file.name for file in uploadedfiles]
            )
            st.session_state["lastuploadcollection"] = targetcollection
            st.session_state["uploadcomplete"] = True
            st.success(
                f"{len(uploadedfiles)} files uploaded and indexed successfully into collection {targetcollection}"
            )

    st.markdown("</div>", unsafe_allow_html=True)


def resolve_source_name(source: dict, index: int | None = None) -> str:
    metadata = source.get("metadata", {}) if isinstance(source, dict) else {}

    candidates = [
        metadata.get("source"),
        metadata.get("title"),
        metadata.get("filename"),
        metadata.get("source_path"),
        source.get("source") if isinstance(source, dict) else None,
        source.get("title") if isinstance(source, dict) else None,
        source.get("filename") if isinstance(source, dict) else None,
        source.get("source_path") if isinstance(source, dict) else None,
    ]

    for value in candidates:
        if not value:
            continue
        try:
            text = str(value).strip()
            if not text:
                continue
            if "/" in text or "\\" in text:
                name = Path(text).name.strip()
                if name:
                    return name
            return text
        except Exception:
            continue

    return f"Source {index}" if index is not None else "Unknown source"


def render_rag_result(result: Any, title: str = "RAG Result") -> None:
    import re

    st.markdown(f"### {title}")

    if not isinstance(result, dict):
        st.write(result)
        return

    answer = result.get("answer") or result.get("analysis") or result.get("response")
    if not answer:
        st.info("No analysis returned.")
        return

    # Show citation audit warnings prominently
    audit_report = result.get("audit_report", "")
    metadata = result.get("metadata") or {}
    hallucination_risk = metadata.get("hallucination_risk", 0.0)
    unverified_citations = metadata.get("unverified_citations", [])

    if unverified_citations or (isinstance(hallucination_risk, (int, float)) and hallucination_risk >= 0.3):
        warning_lines = ["⚠️ Citation Audit Warning"]
        if isinstance(hallucination_risk, (int, float)):
            warning_lines.append(f"Hallucination risk: {hallucination_risk:.0%}")
        if unverified_citations:
            warning_lines.append(f"Unverified citations: {len(unverified_citations)}")
            for c in unverified_citations[:5]:
                warning_lines.append(f"  • {c}")
        warning_lines.append("Do not rely on unverified legal authority without independent confirmation.")
        st.error("\n".join(warning_lines))
    elif audit_report:
        with st.expander("Citation audit report", expanded=False):
            st.markdown(f"<div class='aegis-prose'>{audit_report}</div>", unsafe_allow_html=True)

    # If the answer uses the new legal-brief headings, render each section separately.
    brief_headings = [
        "Executive Summary",
        "Charge and Legislative Framework",
        "Evidence Analysis",
        "Elements of the Offence",
        "Defence Strategies",
        "Pre-Trial Instructions for Lawyer",
        "Evidentiary Issues to Raise",
        "Conclusion and Risk Assessment",
        "Disclaimer",
    ]
    pattern = r"^#\s*(" + "|".join(re.escape(h) for h in brief_headings) + r")\s*$"
    splits = re.split(pattern, answer, flags=re.MULTILINE | re.IGNORECASE)

    if len(splits) > 3:
        # splits[0] is any preamble, then alternating heading/content
        for i in range(1, len(splits), 2):
            heading = splits[i]
            content = splits[i + 1] if i + 1 < len(splits) else ""
            st.markdown(f"#### {heading}")
            st.markdown(
                f"<div class='aegis-prose'>{content.strip()}</div>",
                unsafe_allow_html=True,
            )
    else:
        # Fall back to rendering the raw answer
        st.markdown(answer)

    sources = result.get("sources") or result.get("results") or []
    if sources:
        st.markdown("#### Retrieved Sources")
        for index, source in enumerate(sources, 1):
            if not isinstance(source, dict):
                st.markdown(f"{index}. Source {index}")
                continue

            metadata = source.get("metadata") or {}
            document = (
                source.get("document")
                or source.get("content")
                or source.get("text")
                or ""
            )
            sourcename = resolve_source_name(source, index)
            page = (
                metadata.get("page")
                or metadata.get("pagenumber")
                or source.get("page")
                or source.get("pagenumber")
            )

            if page:
                st.markdown(f"{index}. {sourcename} (page {page})")
            else:
                st.markdown(f"{index}. {sourcename}")

            if document:
                with st.expander(f"Excerpt {index}"):
                    st.write(document)


def show_search() -> None:
    render_brand_header()
    st.markdown("<div class='aegis-panel'>", unsafe_allow_html=True)
    st.markdown("### Search")
    st.markdown(
        "<div class='aegis-note'>Ask a legal question in plain English. AEGIS will return the most relevant verified sources from the indexed legal corpus.</div>",
        unsafe_allow_html=True,
    )

    query = st.text_area("Search query", height=120, key="searchquery")

    if st.button("Run Search", use_container_width=True, key="searchbtn"):
        if not query.strip():
            st.warning("Enter a search query.")
            st.markdown("</div>", unsafe_allow_html=True)
            return

        querytext = query.strip()

        def runrag():
            return api_call(
                "/api/v1/rag",
                data={"query": querytext},
                method="POST",
                apikey=st.session_state.get("apikey"),
                sessionid=st.session_state.get("sessionid"),
            )

        ragresult = run_with_timer(
            "Researching and drafting answer...", runrag
        )

        st.markdown(f"<div class='aegis-note'><strong>Question</strong><br>{querytext}</div>", unsafe_allow_html=True)

        answer = ""
        verifiedsources: list[Any] = []
        if isinstance(ragresult, dict):
            answer = ragresult.get("answer", "")
            if isinstance(ragresult.get("sources"), list):
                verifiedsources = ragresult.get("sources")
            elif isinstance(ragresult.get("results"), list):
                verifiedsources = ragresult.get("results")
        elif isinstance(ragresult, list):
            verifiedsources = ragresult

        if answer:
            st.markdown("### Answer")
            st.markdown(
                f"<div class='aegis-prose'>{answer}</div>",
                unsafe_allow_html=True,
            )
        else:
            st.info("No answer was returned.")

        with st.expander(
            f"View retrieved sources ({len(verifiedsources)})", expanded=False
        ):
            if not verifiedsources:
                st.caption("No verified sources returned from /api/v1/rag.")
            else:
                for index, item in enumerate(verifiedsources, 1):
                    if not isinstance(item, dict):
                        with st.expander(f"{index}. Source {index}", expanded=False):
                            st.write(item)
                        continue

                    metadata = item.get("metadata", {})
                    document = (
                        item.get("document") or item.get("text") or item.get("content")
                    )
                    relevance = item.get("relevance", None)
                    sourcename = resolve_source_name(item, index)
                    category = (
                        metadata.get("category") or item.get("category") or "unknown"
                    )
                    pagenumber = (
                        metadata.get("pagenumber")
                        or metadata.get("page")
                        or item.get("pagenumber")
                        or item.get("page")
                    )

                    bits = [f"Collection {category}"]
                    if pagenumber:
                        bits.append(f"Page {pagenumber}")
                    if relevance is not None:
                        try:
                            bits.append(f"Relevance {float(relevance):.1%}")
                        except Exception:
                            bits.append(f"Relevance {relevance}")

                    with st.expander(f"{index}. {sourcename}", expanded=False):
                        st.caption(" • ".join(bits))
                        if document:
                            st.markdown(
                                f"<div class='aegis-prose'>{document}</div>",
                                unsafe_allow_html=True,
                            )
                        else:
                            st.caption("No preview text returned for this source.")

                        mergedmeta: dict[str, Any] = {}
                        if isinstance(metadata, dict):
                            mergedmeta.update(metadata)
                        for key in (
                            "source",
                            "title",
                            "category",
                            "page",
                            "pagenumber",
                            "relevance",
                        ):
                            if key in item and key not in mergedmeta:
                                mergedmeta[key] = item[key]
                        if mergedmeta:
                            with st.expander("Source metadata", expanded=False):
                                st.json(mergedmeta)

    st.markdown("</div>", unsafe_allow_html=True)


def _navigate_to_collection_inspector(collection: str) -> None:
    """Callback for the Collection Manager Inspect button."""
    st.session_state["inspect_collection"] = collection
    st.session_state["inspect_offset"] = 0
    st.session_state["page"] = "Collection Inspector"
    # Streamlit reruns automatically after a callback; st.rerun() here is a no-op.


def _create_collection_callback() -> None:
    """Callback for the Collection Manager Create collection button."""
    new_name = st.session_state.get("cm_new_name", "").strip()
    new_desc = st.session_state.get("cm_new_desc", "").strip()
    if not new_name:
        st.warning("Enter a collection name.")
        return
    result = api_call(
        f"/api/v1/admin/collections/{new_name}",
        data={"description": new_desc},
        method="POST",
        apikey=st.session_state.get("apikey"),
        sessionid=st.session_state.get("sessionid"),
    )
    if result and result.get("success"):
        st.success(result.get("message"))
        # Streamlit reruns automatically after a callback; st.rerun() here is a no-op.
    else:
        st.error("Failed to create collection.")


def show_collection_manager() -> None:
    """Admin/staff collection management page."""
    render_brand_header()
    st.markdown("<div class='aegis-panel'>", unsafe_allow_html=True)
    st.markdown("### Collection Manager")

    collections = get_existing_collections()

    with st.expander("➕ Create new collection", expanded=False):
        st.text_input("Collection name", key="cm_new_name", placeholder="e.g. police-disclosure-june-2026")
        st.text_input("Description (optional)", key="cm_new_desc", placeholder="Brief description")
        st.button(
            "Create collection",
            key="cm_create_btn",
            on_click=_create_collection_callback,
        )

    if not collections:
        st.info("No collections found.")
    else:
        st.markdown(f"**{len(collections)} collection(s) found**")
        for col in collections:
            c1, c2 = st.columns([4, 1])
            with c1:
                st.markdown(f"- **{col}**")
            with c2:
                st.button(
                    "Inspect",
                    key=f"cm_inspect_{col}",
                    on_click=_navigate_to_collection_inspector,
                    args=(col,),
                )

    st.markdown("</div>", unsafe_allow_html=True)


def show_collection_inspector() -> None:
    """Browse chunks inside a selected collection."""
    render_brand_header()
    st.markdown("<div class='aegis-panel'>", unsafe_allow_html=True)
    st.markdown("### Collection Inspector")

    collections = get_existing_collections()
    current = st.session_state.get("inspect_collection")
    if current not in collections:
        current = None
    selected = st.selectbox(
        "Select collection",
        options=collections,
        index=collections.index(current) if current in collections else 0,
        key="ci_select",
    )
    if selected != current:
        st.session_state["inspect_collection"] = selected
        st.session_state["inspect_offset"] = 0
        st.session_state.pop("inspect_result", None)
        st.rerun()

    offset = st.session_state.get("inspect_offset", 0)
    limit = st.selectbox("Chunks per page", [10, 20, 50, 100], index=1, key="ci_limit")

    if st.button("Load chunks", key="ci_load"):
        result = api_call(
            f"/api/v1/admin/collections/{selected}/inspect",
            data={"offset": offset, "limit": limit},
            method="GET",
            apikey=st.session_state.get("apikey"),
            sessionid=st.session_state.get("sessionid"),
        )
        if result:
            st.session_state["inspect_result"] = result

    result = st.session_state.get("inspect_result")
    if result and result.get("name") == selected:
        st.markdown(f"**{result.get('total', 0)} total chunks** - showing {len(result.get('items', []))}")
        if result.get("unique_sources"):
            st.caption("Sources: " + ", ".join(str(s) for s in result["unique_sources"]))

        for i, item in enumerate(result.get("items", []), start=offset + 1):
            meta = item.get("metadata", {}) or {}
            source = meta.get("filename") or meta.get("source") or meta.get("title") or "unknown"
            page = meta.get("page") or meta.get("pagenumber") or meta.get("page_number")
            header = f"Chunk {i}: {source}"
            if page:
                header += f" (page {page})"
            with st.expander(header):
                st.caption(f"ID: {item.get('id', 'N/A')}")
                st.json(meta)
                st.markdown(item.get("document", "")[:2000])

        # Pagination
        total = result.get("total", 0)
        col1, col2, col3 = st.columns(3)
        with col1:
            if offset > 0 and st.button("← Previous", key="ci_prev"):
                st.session_state["inspect_offset"] = max(0, offset - limit)
                st.rerun()
        with col2:
            st.write(f"Offset {offset}")
        with col3:
            if offset + limit < total and st.button("Next →", key="ci_next"):
                st.session_state["inspect_offset"] = offset + limit
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def show_adminpanel() -> None:
    """Admin dashboard with database stats and active user monitoring."""
    render_brand_header()
    st.markdown("<div class='aegis-panel'>", unsafe_allow_html=True)
    st.markdown("### 🛡️ Admin Panel")
    st.markdown(
        "<div class='aegis-note'>System monitoring and database statistics.</div>",
        unsafe_allow_html=True,
    )

    admin_key = os.getenv("ADMIN_API_KEY", "")
    if not admin_key:
        st.warning("ADMIN_API_KEY not set in environment.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    token = st.session_state.get("apikey")
    if not token:
        st.error("Not authenticated. Please log in.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    headers = {"Authorization": f"Bearer {token}"}
    base_url = "http://127.0.0.1:8000"

    # ─── Database Stats Button ───────────────────────────────────────────────
    if st.button(
        "📊 Refresh Database Stats",
        type="primary",
        use_container_width=True,
        key="admin_stats_btn",
    ):
        with st.spinner("Loading stats..."):
            try:
                import requests

                resp = requests.get(
                    f"{base_url}/api/v1/admin/stats?admin_key={admin_key}",
                    headers=headers,
                    timeout=30,
                )
                if resp.status_code == 200:
                    stats = resp.json()
                    st.markdown("---")
                    st.markdown("#### 📈 Database Statistics")

                    cols = st.columns(3)
                    with cols[0]:
                        st.metric("📁 Collections", len(stats.get("collections", [])))
                    with cols[1]:
                        st.metric("📄 Total Documents", stats.get("total_documents", 0))
                    with cols[2]:
                        st.metric("👥 Active Users", stats.get("total_active_users", 0))

                    collections = stats.get("collections", [])
                    if collections:
                        st.markdown("#### 📁 Collections Breakdown")
                        for col in collections:
                            name = col.get("name", "Unknown")
                            desc = col.get("description", "")
                            count = col.get("document_count", 0)
                            st.markdown(
                                f"**{name}** - {desc}  <span style='color:#c5a880;'>{
                                    count:,} docs</span>", unsafe_allow_html=True
                            )

                    st.caption(f"Last updated: {
                        stats.get(
                            'timestamp',
                            'N/A')}")
                else:
                    st.error(f"API Error {resp.status_code}: {resp.text[:200]}")
            except Exception as e:
                st.error(f"Error: {e}")

    # ─── Active Users Button ─────────────────────────────────────────────────
    if st.button(
        "👥 Show Active Users",
        type="primary",
        use_container_width=True,
        key="admin_users_btn",
    ):
        with st.spinner("Loading users..."):
            try:
                import requests

                resp = requests.get(
                    f"{base_url}/api/v1/admin/users?admin_key={admin_key}",
                    headers=headers,
                    timeout=30,
                )
                if resp.status_code == 200:
                    users_data = resp.json()
                    st.markdown("---")
                    st.markdown("#### 👥 Active Users")

                    total = users_data.get("total_active_users", 0)
                    st.metric("Total Active Users", total)

                    users = users_data.get("users", [])
                    if users:
                        user_rows = []
                        for u in users:
                            user_rows.append(
                                {
                                    "Type": u.get("type", "unknown"),
                                    "Username": u.get("username", "N/A"),
                                    "Name": u.get("name", "N/A"),
                                    "Email": u.get("email", "N/A"),
                                    "Role": u.get("role", "N/A"),
                                    "Expires": (
                                        u.get("expires_at", "N/A")[:19]
                                        if u.get("expires_at")
                                        else "N/A"
                                    ),
                                }
                            )
                        st.dataframe(
                            user_rows, use_container_width=True, hide_index=True
                        )
                    else:
                        st.info("No active users found.")

                    st.caption(f"Last updated: {
                        users_data.get(
                            'timestamp',
                            'N/A')}")
                else:
                    st.error(f"API Error {resp.status_code}: {resp.text[:200]}")
            except Exception as e:
                st.error(f"Error: {e}")

    st.markdown("</div>", unsafe_allow_html=True)
    return



# ─── Disclosure Upload ────────────────────────────────────────────────────


def _render_disclosure_uploader(upload_key: str = "disclosurefileupload") -> None:
    """Render the disclosure file uploader and process uploaded files.

    Plain text files are appended to st.session_state["disclosure_file_content"];
    binary files (PDF/DOCX/RTF) are uploaded to a temporary session collection
    stored in st.session_state["lastuploadcollection"].
    """
    st.caption("Upload disclosure documents. Plain text files are read directly; PDF/DOCX/RTF are parsed on the server.")
    disclosure_files = st.file_uploader(
        "Upload disclosure documents",
        type=["txt", "md", "pdf", "docx", "doc", "rtf"],
        accept_multiple_files=True,
        key=upload_key,
    )

    loaded_messages: list[str] = []
    if disclosure_files:
        processed_files = set(st.session_state.get("disclosure_processed_files", []))
        new_filenames: set[str] = set()

        # Deduplicate by filename within this run so reruns/button clicks cannot
        # multiply the same file in the widget state.
        seen_filenames: set[str] = set()
        unique_files: list = []
        for f in disclosure_files:
            if f.name in seen_filenames:
                continue
            seen_filenames.add(f.name)
            unique_files.append(f)

        text_parts = []
        binary_files = []
        new_binary_files = []
        for f in unique_files:
            if f.name.lower().endswith((".txt", ".md")):
                try:
                    decoded = f.getvalue().decode("utf-8", errors="ignore")
                    text_parts.append(decoded)
                    if f.name not in processed_files:
                        loaded_messages.append(f"Loaded {len(decoded):,} characters from {f.name}")
                        new_filenames.add(f.name)
                except Exception as e:
                    st.error(f"Could not read {f.name}: {e}")
            else:
                binary_files.append(f)
                if f.name not in processed_files:
                    new_binary_files.append(f)
                    new_filenames.add(f.name)

        # Replace text content with the current set of uploaded text files.
        # This avoids the append-doubling bug across Streamlit reruns/button clicks.
        st.session_state["disclosure_file_content"] = (
            "\n\n".join(text_parts).strip() if text_parts else ""
        )

        # Only upload binary files once to the temp collection.
        if new_binary_files:
            target_collection = f"temp_session_{st.session_state.get('sessionid', 'default')}"
            with st.spinner(f"Uploading {len(new_binary_files)} document(s) for parsing..."):
                upload_result = api_call(
                    "/api/v1/upload/files",
                    data={"collection": target_collection},
                    method="POST",
                    apikey=st.session_state.get("apikey"),
                    sessionid=st.session_state.get("sessionid"),
                    files=new_binary_files,
                    filefieldname="files",
                )

            if upload_result:
                uploaded_names = [f.name for f in new_binary_files]
                st.session_state["uploadeddocuments"] = (
                    st.session_state.get("uploadeddocuments", []) + uploaded_names
                )
                st.session_state["lastuploadcollection"] = target_collection
                st.success(
                    f"{len(new_binary_files)} file(s) uploaded and indexed for analysis."
                )
            else:
                st.error("Upload failed for one or more documents.")

        if new_filenames:
            st.session_state["disclosure_processed_files"] = list(
                processed_files | new_filenames
            )

        for msg in loaded_messages:
            st.success(msg)


def show_disclosure_upload() -> None:
    """Temporary session upload of police disclosure documents for later analysis."""
    render_brand_header()
    st.markdown("<div class='aegis-panel'>", unsafe_allow_html=True)
    st.markdown("### Disclosure Upload")
    st.markdown(
        "<div class='aegis-note'>Upload police disclosure documents to this temporary session. "
        "They will be parsed and indexed for Defence Analysis only. These documents are not added to any permanent collection.</div>",
        unsafe_allow_html=True,
    )

    # ─── Previously uploaded documents ──────────────────────────────────────
    uploadeddocs = st.session_state.get("uploadeddocuments", [])
    if uploadeddocs:
        files_html = "".join(f"<li>{name}</li>" for name in uploadeddocs)
        st.markdown(
            f"<div class='aegis-list'><strong>Documents already uploaded to this session</strong><ul>{files_html}</ul></div>",
            unsafe_allow_html=True,
        )

    # ─── File upload input ───────────────────────────────────────────────────
    _render_disclosure_uploader("disclosurefileupload")

    if st.button("Go to Defence Analysis", use_container_width=True, key="gotodefencebtn"):
        st.session_state["page"] = "Defence Analysis"
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# ─── Defence Analysis ───────────────────────────────────────────────────────


def show_defence_analysis() -> None:
    """Defence Analysis page - full pipeline with timer, expert analysis, auto-scroll, print."""
    import time
    import datetime

    render_brand_header()
    st.markdown("<div class='aegis-panel'>", unsafe_allow_html=True)
    st.markdown("### Defence Analysis")
    st.markdown(
        "<div class='aegis-note'>Upload disclosure documents below. "
        "AEGIS will run a full expert defence analysis.</div>",
        unsafe_allow_html=True,
    )

    # ─── Previously uploaded documents ──────────────────────────────────────
    uploadeddocs = st.session_state.get("uploadeddocuments", [])
    has_uploaded_docs = bool(uploadeddocs)
    if has_uploaded_docs:
        files_html = "".join(f"<li>{name}</li>" for name in uploadeddocs)
        st.markdown(
            f"<div class='aegis-list'><strong>Documents already uploaded to this session</strong><ul>{files_html}</ul></div>",
            unsafe_allow_html=True,
        )
        st.caption("These uploaded documents are automatically included in the analysis.")

    # ─── File upload input ───────────────────────────────────────────────────
    _render_disclosure_uploader("defencefileupload")

    disclosure_text = st.session_state.get("disclosure_file_content") or ""
    has_text = bool(disclosure_text and len(disclosure_text.strip()) >= 50)
    can_analyze = has_text or has_uploaded_docs

    # ─── Analysis Button ───────────────────────────────────────────────────
    analyze_btn = st.button(
        "Run Defence Analysis",
        type="primary",
        use_container_width=True,
        key="multianalyzebtn",
        disabled=not can_analyze,
    )

    # ─── Input summary and preview under the button ─────────────────────────
    if can_analyze:
        char_count = len(disclosure_text.strip()) if has_text else 0
        preview_text = f"📝 {char_count:,} characters of text"
        with st.expander(f"Analysis input preview - {preview_text}", expanded=False):
            if has_text:
                preview = disclosure_text[:1000] + ("..." if len(disclosure_text) > 1000 else "")
                st.markdown(f"<span style='color:#555555;'>{preview}</span>", unsafe_allow_html=True)
            elif has_uploaded_docs:
                st.caption("Only uploaded documents will be analysed.")

    # ─── Results container (will be filled after analysis) ───────────────────
    results_container = st.container()

    # Persist results so export-button reruns do not wipe the brief from the page.
    if analyze_btn and can_analyze:
        # If a previous attempt failed, clear the stale failure banner and rerun once
        # so the user does not see a dimmed "Analysis failed" message while the new
        # long-running analysis is in progress.
        had_error = st.session_state.get("analysis_failed") or st.session_state.get("last_api_error")
        st.session_state["last_api_error"] = None
        st.session_state["analysis_failed"] = False
        if had_error:
            st.rerun()
        start_time = time.time()

        def run_analysis():
            return api_call(
                "/api/v1/analyse/disclosure",
                data={
                    "disclosure_text": disclosure_text.strip(),
                    "analysis_type": "full",
                    "uploaded_collection": st.session_state.get("lastuploadcollection"),
                },
                method="POST",
                apikey=st.session_state.get("apikey"),
                sessionid=st.session_state.get("sessionid"),
                readtimeout=900,
            )

        result = run_with_timer("Conducting Expert Analysis...", run_analysis)

        elapsed = round(time.time() - start_time, 2)
        server_time = (
            result.get("processing_time_seconds", elapsed) if result else elapsed
        )

        st.session_state["analysis_result"] = result
        st.session_state["analysis_elapsed"] = elapsed
        st.session_state["analysis_server_time"] = server_time
        # Flag a real failed attempt so the error banner only appears when relevant.
        if not result or not result.get("success"):
            st.session_state["analysis_failed"] = True

    result = st.session_state.get("analysis_result")
    elapsed = st.session_state.get("analysis_elapsed")
    server_time = st.session_state.get("analysis_server_time")

    if result and result.get("success"):
        with results_container:
            # ─── Timer Display ───────────────────────────────────────────
            st.markdown("---")
            timer_cols = st.columns([1, 1, 1])
            with timer_cols[0]:
                st.metric("⏱️ Total Time", f"{elapsed}s")
            with timer_cols[1]:
                st.metric("🤖 Server Time", f"{server_time}s")
            with timer_cols[2]:
                input_len = (result.get("metadata") or {}).get("input_length", len(disclosure_text) or 0)
                st.metric("📄 Text Length", f"{input_len:,} chars")

            # ─── Citation Audit Warning ──────────────────────────────────
            metadata = result.get("metadata") or {}
            hallucination_risk = metadata.get("hallucination_risk", 0.0)
            unverified_citations = metadata.get("unverified_citations", [])
            if unverified_citations or (
                isinstance(hallucination_risk, (int, float)) and hallucination_risk >= 0.3
            ):
                warning_lines = ["⚠️ Citation Audit Warning"]
                if isinstance(hallucination_risk, (int, float)):
                    warning_lines.append(f"Hallucination risk: {hallucination_risk:.0%}")
                warning_lines.append(f"Unverified citations: {len(unverified_citations)}")
                for c in unverified_citations[:5]:
                    warning_lines.append(f"  • {c}")
                warning_lines.append(
                    "Do not rely on unverified legal authority without independent confirmation."
                )
                st.error("\n".join(warning_lines))

            # ─── Legal Brief Output ──────────────────────────────────────
            st.markdown("---")
            st.markdown("## 📋 Defence Analysis Brief")

            sections = [
                ("title_block", "Legal Analysis & Defence Instructions"),
                ("table_of_contents", "Table of Contents"),
                ("executive_summary", "Executive Summary"),
                ("charge_and_legislative_framework", "Charge and Legislative Framework"),
                ("summary_of_evidence", "Summary of Evidence"),
                ("assessment_of_prosecution_case", "Assessment of Prosecution Case"),
                ("elements_of_the_offence", "Elements the Prosecution Must Prove"),
                ("defence_strategies", "Defence Strategies and Options"),
                ("cross_examination_priorities", "Cross-Examination Priorities"),
                ("disclosure_and_forensic_gaps", "Disclosure and Forensic Gaps"),
                ("instructions_to_counsel_pre_trial", "Instructions to Counsel Pre-Trial"),
                ("evidentiary_issues_to_raise", "Evidentiary Issues to Raise"),
                ("conclusion", "Conclusion"),
            ]

            for key, title in sections:
                content = result.get(key, "")
                # Fallback to legacy/alternate fields if new field is empty
                if not content:
                    if key == "charge_and_legislative_framework":
                        content = result.get("charge_analysis", "")
                    elif key == "instructions_to_counsel_pre_trial":
                        content = result.get("pre_trial_instructions_for_lawyer", "") or result.get("options_and_recommendations", "")
                    elif key == "conclusion":
                        content = result.get("conclusion_and_risk_assessment", "") or result.get("risk_assessment", "")

                st.markdown(f"### {title}")
                if content:
                    st.markdown(
                        f"<div class='aegis-prose'>{content}</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.info(f"No {title.lower()} returned.")

            disclaimer = result.get("disclaimer", "")
            if disclaimer:
                st.warning(disclaimer)
            else:
                st.warning(
                    "This analysis is generated by AI and does not constitute legal advice. Consult a qualified New Zealand lawyer."
                )

            # ─── Export Buttons ──────────────────────────────────────────
            st.markdown("---")
            st.markdown("**Defence Analysis Brief**")
            pdf_col, docx_col = st.columns([1, 1])
            now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M")
            with pdf_col:
                try:
                    pdf_buffer = build_pdf(result, elapsed=elapsed, server_time=server_time)
                    st.download_button(
                        label="📕 Download PDF",
                        data=pdf_buffer.getvalue(),
                        file_name=f"aegis_analysis_{now_str}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        key="pdfdownloadbtn",
                        type="primary",
                    )
                except Exception as e:
                    st.caption(f"PDF export unavailable: {e}")
            with docx_col:
                try:
                    docx_buffer = build_docx(result)
                    st.download_button(
                        label="📄 Download DOCX",
                        data=docx_buffer.getvalue(),
                        file_name=f"aegis_analysis_{now_str}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True,
                        key="docxdownloadbtn",
                        type="primary",
                    )
                except Exception as e:
                    st.caption(f"DOCX export unavailable: {e}")

            st.markdown("---")
            st.markdown("**Criminal Disclosure Analysis Report**")
            dis_pdf_col, dis_docx_col = st.columns([1, 1])
            with dis_pdf_col:
                try:
                    dis_pdf_buffer = build_disclosure_pdf(result, elapsed=elapsed, server_time=server_time)
                    st.download_button(
                        label="📕 Download Disclosure PDF",
                        data=dis_pdf_buffer.getvalue(),
                        file_name=f"aegis_disclosure_{now_str}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        key="disclosurepdfdownloadbtn",
                    )
                except Exception as e:
                    st.caption(f"Disclosure PDF export unavailable: {e}")
            with dis_docx_col:
                try:
                    dis_docx_buffer = build_disclosure_docx(result)
                    st.download_button(
                        label="📄 Download Disclosure DOCX",
                        data=dis_docx_buffer.getvalue(),
                        file_name=f"aegis_disclosure_{now_str}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True,
                        key="disclosuredocxdownloadbtn",
                    )
                except Exception as e:
                    st.caption(f"Disclosure DOCX export unavailable: {e}")

            # ─── Auto-scroll to results ──────────────────────────────────
            st.html(
                """
            <div style="height:0;overflow:hidden;">
            <script>
            setTimeout(function() {
                var main = document.querySelector('section.main');
                if (main) {
                    var metrics = document.querySelectorAll('[data-testid="stMetricValue"]');
                    if (metrics.length > 0) {
                        metrics[0].scrollIntoView({ behavior: 'smooth', block: 'start' });
                    } else {
                        var headings = main.querySelectorAll('h2, h3');
                        if (headings.length > 0) {
                            headings[0].scrollIntoView({ behavior: 'smooth', block: 'start' });
                        }
                    }
                }
            }, 800);
            </script>
            </div>
            """
            )

            # ─── Deep Dive ───────────────────────────────────────────────
            st.markdown("---")
            st.markdown("## 🔍 Deep Dive")
            st.markdown(
                "<div class='aegis-note'>Ask AEGIS to go deeper on a specific issue from the disclosure. "
                "Examples: <em>search warrant validity</em>, <em>identification evidence</em>, "
                "<em>voluntariness of admissions</em>, <em>disclosure gaps</em>.</div>",
                unsafe_allow_html=True,
            )

            focus_area = st.text_area(
                "What would you like AEGIS to explore in depth?",
                value=st.session_state.get("deep_focus_area", ""),
                height=100,
                key="deepfocusinput",
            )

            if st.button("Run Deep Analysis", use_container_width=True, key="deepanalyzebtn"):
                if not focus_area.strip():
                    st.warning("Enter a focus area for the deep analysis.")
                else:
                    st.session_state["deep_focus_area"] = focus_area.strip()

                    def run_deep():
                        return api_call(
                            "/api/v1/analyse/disclosure/deep",
                            data={
                                "focus_area": focus_area.strip(),
                                "disclosure_text": disclosure_text.strip(),
                                "uploaded_collection": st.session_state.get("lastuploadcollection"),
                                "previous_analysis": result.get("executive_summary", ""),
                            },
                            method="POST",
                            apikey=st.session_state.get("apikey"),
                            sessionid=st.session_state.get("sessionid"),
                            readtimeout=900,
                        )

                    deep_result = run_with_timer("Conducting deep analysis...", run_deep)
                    if deep_result:
                        st.session_state["deep_analysis_result"] = deep_result

            deep_result = st.session_state.get("deep_analysis_result")
            if deep_result and deep_result.get("success"):
                st.markdown("### Deep Analysis Result")
                evidence = deep_result.get("evidence_analysis", "")
                if evidence:
                    st.markdown(
                        f"<div class='aegis-prose'>{evidence}</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.info("No deep analysis content returned.")

                strategies = deep_result.get("defence_strategies", "")
                if strategies:
                    st.markdown("#### Strategic Notes")
                    st.markdown(
                        f"<div class='aegis-prose'>{strategies}</div>",
                        unsafe_allow_html=True,
                    )

                deep_meta = deep_result.get("metadata") or {}
                deep_hallucination = deep_meta.get("hallucination_risk", 0.0)
                deep_unverified = deep_meta.get("unverified_citations", [])
                if deep_unverified or (
                    isinstance(deep_hallucination, (int, float)) and deep_hallucination >= 0.3
                ):
                    warning_lines = ["⚠️ Deep Analysis Citation Warning"]
                    if isinstance(deep_hallucination, (int, float)):
                        warning_lines.append(f"Hallucination risk: {deep_hallucination:.0%}")
                    warning_lines.append(f"Unverified citations: {len(deep_unverified)}")
                    for c in deep_unverified[:5]:
                        warning_lines.append(f"  • {c}")
                    st.error("\n".join(warning_lines))

                st.warning(deep_result.get("disclaimer", "This analysis is generated by AI and does not constitute legal advice."))

    elif analyze_btn and can_analyze and st.session_state.get("analysis_failed"):
        st.error("Analysis failed. Please check your input and try again.")
        last_error = st.session_state.get("last_api_error")
        if last_error:
            st.markdown(
                f"<div style='color:#a94442;background:#f2dede;padding:10px;border-radius:4px;'>"
                f"<strong>Server response:</strong><br>{last_error}</div>",
                unsafe_allow_html=True,
            )
        if result:
            st.json(result)

    st.markdown("</div>", unsafe_allow_html=True)


def show_email_inbox():
    render_brand_header()
    st.markdown("<div class='aegis-panel'>", unsafe_allow_html=True)
    st.title("📧 Email Inbox")
    st.caption("Disclosure submissions received by email.")

    status_filter = st.selectbox(
        "Status",
        ["all", "received", "parsing", "analysing", "completed", "failed", "quarantined"],
        key="email_status_filter",
    )
    days = st.slider("Days", 1, 30, 7, key="email_days_slider")
    apikey = st.session_state.get("apikey")

    if st.button("🔄 Fetch now", key="email_fetch_now"):
        result = api_call(
            "/api/v1/email/fetch",
            method="POST",
            apikey=apikey,
            sessionid=st.session_state.get("sessionid"),
            readtimeout=120,
        )
        if isinstance(result, dict) and result.get("status") == "ok":
            st.success("Fetch triggered")
        else:
            st.error(f"Fetch failed: {result}")

    params = {"days": days, "limit": 200}
    if status_filter != "all":
        params["status"] = status_filter
    result = api_call(
        "/api/v1/email/jobs",
        method="GET",
        data=params,
        apikey=apikey,
        sessionid=st.session_state.get("sessionid"),
        readtimeout=30,
    )
    if not isinstance(result, dict):
        st.error(f"Failed to load jobs: {result}")
        st.markdown("</div>", unsafe_allow_html=True)
        return
    jobs = result.get("jobs", [])

    st.write(f"Found {len(jobs)} job(s)")
    for job in jobs:
        with st.expander(
            f"{job.get('subject')} — {job.get('status')} ({job.get('sender')})"
        ):
            st.write(f"Received: {job.get('received_at')}")
            st.write(f"Attachments: {job.get('attachment_count')}")
            st.write(f"Retries: {job.get('retry_count')}")
            if job.get("error_message"):
                st.error(job.get("error_message"))
            if job.get("result_path"):
                try:
                    report_bytes = api_call_raw(
                        f"/api/v1/email/jobs/{job.get('id')}/report",
                        method="GET",
                        apikey=apikey,
                        sessionid=st.session_state.get("sessionid"),
                        readtimeout=60,
                    )
                    if isinstance(report_bytes, bytes):
                        mime = "application/octet-stream"
                        if job.get("result_path", "").endswith(".docx"):
                            mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                        elif job.get("result_path", "").endswith(".pdf"):
                            mime = "application/pdf"
                        elif job.get("result_path", "").endswith(".txt"):
                            mime = "text/plain"
                        st.download_button(
                            label="Download report",
                            data=report_bytes,
                            file_name=os.path.basename(job.get("result_path")),
                            mime=mime,
                            key=f"dl_report_{job.get('id')}",
                        )
                    else:
                        st.error("Report download failed")
                except Exception as exc:
                    st.error(f"Report download failed: {exc}")
            if job.get("status") in ("failed", "quarantined"):
                if st.button("Retry", key=f"retry_{job.get('id')}"):
                    rr = api_call(
                        f"/api/v1/email/jobs/{job.get('id')}/retry",
                        method="POST",
                        apikey=apikey,
                        sessionid=st.session_state.get("sessionid"),
                        readtimeout=120,
                    )
                    if isinstance(rr, dict) and rr.get("success"):
                        st.success("Retry triggered")
                        st.rerun()
                    else:
                        st.info(
                            rr.get("detail", str(rr))
                            if isinstance(rr, dict)
                            else (rr if isinstance(rr, str) else "Retry failed")
                        )

    st.markdown("</div>", unsafe_allow_html=True)


# ─── Main ───────────────────────────────────────────────────────────────


def main() -> None:
    init_session()

    # FIXED: Check for apikey presence (handles None and empty string)
    if not st.session_state.get("apikey"):
        login()
        return

    page = show_sidebar()

    if page == "Home":
        show_home()
    elif page == "Upload":
        show_upload()
    elif page == "Disclosure Upload":
        show_disclosure_upload()
    elif page == "Collection Manager":
        show_collection_manager()
    elif page == "Collection Inspector":
        show_collection_inspector()
    elif page == "Search":
        show_search()
    elif page == "Defence Analysis":
        show_defence_analysis()
    elif page == "Admin Panel":
        show_adminpanel()
    elif page == "Email Inbox":
        show_email_inbox()


if __name__ == "__main__":
    main()
