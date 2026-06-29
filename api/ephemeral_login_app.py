#!/usr/bin/env python3
from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
import streamlit as st
import chromadb


st.set_page_config(
    page_title="AEGIS - NZ's Legal Assistant",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

APIURL = os.getenv("APIURL", "http://127.0.0.1:8000")
CHROMADBPATH = os.getenv("CHROMADBPATH", "/workspace/chroma_db_fresh")


def load_css(filename: str = "theme.css") -> None:
    css_path = Path.cwd() / filename
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


load_css()


def init_session() -> None:
    st.session_state.setdefault("apikey", None)
    st.session_state.setdefault("sessionid", str(uuid.uuid4()))
    st.session_state.setdefault("tenantinfo", None)
    st.session_state.setdefault("page", "Home")
    st.session_state.setdefault("uploadeddocuments", [])
    st.session_state.setdefault("demoemail", "")
    st.session_state.setdefault("demophone", "")
    st.session_state.setdefault("challengeid", "")
    st.session_state.setdefault("accesscode", "")
    st.session_state.setdefault("democodesent", False)
    st.session_state.setdefault("role", None)
    st.session_state.setdefault("tenantid", None)
    st.session_state.setdefault("displayname", None)
    st.session_state.setdefault("quotas", None)
    st.session_state.setdefault("authmode", None)
    st.session_state.setdefault("staffusername", "")


def reset_auth_state() -> None:
    keys = [
        "apikey",
        "tenantinfo",
        "challengeid",
        "accesscode",
        "democodesent",
        "uploadeddocuments",
        "role",
        "tenantid",
        "displayname",
        "quotas",
        "authmode",
        "demoemail",
        "demophone",
        "staffusername",
    ]
    for key in keys:
        if key in st.session_state:
            del st.session_state[key]
    st.session_state["apikey"] = None
    st.session_state["tenantinfo"] = None
    st.session_state["challengeid"] = ""
    st.session_state["accesscode"] = ""
    st.session_state["democodesent"] = False
    st.session_state["uploadeddocuments"] = []
    st.session_state["page"] = "Home"
    st.session_state["sessionid"] = str(uuid.uuid4())


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
    base = APIURL if APIURL.endswith("/") else APIURL + "/"
    url = urljoin(base, endpoint.lstrip("/"))
    headers = {}

    if apikey:
        headers["Authorization"] = f"Bearer {apikey}"
    if sessionid:
        headers["X-Session-ID"] = sessionid

    try:
        if files:
            multipartfiles = []
            for f in files:
                mime = getattr(f, "type", None) or "application/octet-stream"
                multipartfiles.append((filefieldname, (f.name, f.getvalue(), mime)))

            formdata = {}
            if isinstance(data, dict):
                for k, v in data.items():
                    if v is not None:
                        formdata[k] = str(v)

            resp = requests.request(
                method.upper(),
                url,
                headers=headers,
                data=formdata,
                files=multipartfiles,
                timeout=(connecttimeout, readtimeout),
            )
        else:
            if method.upper() == "GET":
                resp = requests.get(
                    url,
                    headers=headers,
                    params=data,
                    timeout=(connecttimeout, readtimeout),
                )
            else:
                resp = requests.request(
                    method.upper(),
                    url,
                    headers=headers,
                    json=data,
                    timeout=(connecttimeout, readtimeout),
                )

        resp.raise_for_status()
        ctype = resp.headers.get("content-type", "")
        if "application/json" in ctype:
            return resp.json()
        return {"text": resp.text, "status_code": resp.status_code}

    except requests.HTTPError as e:
        detail = None
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text if "resp" in locals() else str(e)
        if not quiet:
            st.error(f"API error: {e} - {detail}")
        return None
    except Exception as e:
        if not quiet:
            st.error(f"API error: {e}")
        return None


def render_brand_header(showstickman: bool = False) -> None:
    emoji = "🕴️" if showstickman else "⚖️"
    st.markdown(
        f"""
        <div style='padding: 0.5rem 0 1rem 0;'>
            <div style='font-size: 0.9rem; color: #666;'>NZ's Legal Assistant</div>
            <h1 style='margin: 0.1rem 0;'>{emoji} AEGIS</h1>
            <div style='color: #666;'>Secure Legal Research</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_stickman_loader(message: str = "Working behind the scenes...") -> None:
    st.info(message)


def run_with_stickman(message: str, fn):
    loader_slot = st.empty()
    try:
        with loader_slot.container():
            render_stickman_loader(message)
            with st.spinner(message, show_time=True):
                return fn()
    finally:
        loader_slot.empty()


def login() -> None:
    render_brand_header(showstickman=False)
    clienttab, stafftab = st.tabs(["Client Access", "Staff / Admin"])

    with clienttab:
        st.markdown("## Client Access")
        st.info("Users sign in with an ephemeral access code. No password login is available.")

        email = st.text_input("Email", value=st.session_state.get("demoemail", ""), key="loginemail")
        phone = st.text_input("Phone", value=st.session_state.get("demophone", ""), key="loginphone")

        if st.button("Send Access Code", use_container_width=True, key="loginsendcode"):
            if not email.strip() or not phone.strip():
                st.warning("Email and phone are required.")
            else:
                result = api_call(
                    "auth/demo/start",
                    data={
                        "email": email.strip(),
                        "phone": phone.strip(),
                    },
                    method="POST",
                    sessionid=st.session_state["sessionid"],
                )
                if result:
                    st.session_state["demoemail"] = email.strip()
                    st.session_state["demophone"] = phone.strip()
                    st.session_state["challengeid"] = result.get("challenge_id", "")
                    st.session_state["accesscode"] = result.get("access_code", "")
                    st.session_state["democodesent"] = True
                    st.success("Access code issued.")
                    st.rerun()

        if st.session_state.get("democodesent", False):
            st.markdown("### Access Code")
            if st.session_state.get("accesscode", "").strip():
                st.success(f"Access code received: {st.session_state['accesscode']}")
            else:
                st.warning("Challenge created, but no access code was returned.")

            code = st.text_input(
                "Enter Access Code",
                value=st.session_state.get("accesscode", ""),
                key="logincode",
            )

            if st.button("Enter App", type="primary", use_container_width=True, key="loginenterapp"):
                if not code.strip():
                    st.warning("Access code is required.")
                elif not st.session_state.get("challengeid", "").strip():
                    st.warning("Challenge ID is missing. Please request a new access code.")
                else:
                    result = api_call(
                        "auth/demo/verify",
                        data={
                            "challenge_id": st.session_state["challengeid"].strip(),
                            "access_code": code.strip(),
                        },
                        method="POST",
                        sessionid=st.session_state["sessionid"],
                    )
                    if result:
                        st.session_state["authmode"] = "client"
                        st.session_state["role"] = result.get("role", "user")
                        st.session_state["tenantid"] = result.get("tenant_id")
                        st.session_state["displayname"] = result.get("name") or result.get("username") or "Client User"
                        st.session_state["apikey"] = result.get("api_key")
                        st.session_state["quotas"] = result.get("quotas")
                        st.session_state["tenantinfo"] = result
                        st.success("Access granted.")
                        st.rerun()

    with stafftab:
        st.markdown("## Staff / Admin Login")
        st.info("Privileged users sign in with username and password.")

        staffusername = st.text_input(
            "Username",
            value=st.session_state.get("staffusername", ""),
            key="staffloginusername",
        )
        staffpassword = st.text_input(
            "Password",
            type="password",
            key="staffloginpassword",
        )

        if st.button("Sign In", type="primary", use_container_width=True, key="staffloginbutton"):
            if not staffusername.strip() or not staffpassword.strip():
                st.warning("Username and password are required.")
            else:
                result = api_call(
                    "api/v1/login",
                    data={
                        "username": staffusername.strip(),
                        "password": staffpassword,
                    },
                    method="POST",
                    sessionid=st.session_state["sessionid"],
                )
                if result:
                    role = str(result.get("role", "staff")).strip().lower()
                    st.session_state["authmode"] = "staff"
                    st.session_state["staffusername"] = staffusername.strip()
                    st.session_state["role"] = role
                    st.session_state["tenantid"] = result.get("tenant_id")
                    st.session_state["displayname"] = result.get("name", staffusername.strip())
                    st.session_state["apikey"] = result.get("api_key")
                    st.session_state["quotas"] = result.get("quotas")
                    st.session_state["tenantinfo"] = result
                    st.success(f"Signed in as {st.session_state['displayname']}.")
                    st.rerun()


def show_sidebar() -> str:
    with st.sidebar:
        st.markdown("# AEGIS")
        st.caption("NZ's Legal Assistant")

        role = str(st.session_state.get("role", "client")).lower().strip()
        displayname = (
            st.session_state.get("displayname")
            or st.session_state.get("staffusername")
            or st.session_state.get("demoemail")
            or "Authenticated user"
        )

        st.info(f"Signed in as {displayname}")
        st.caption(f"Role: {role}")

        if role == "admin":
            pages = ["Home", "Upload", "Collection Manager", "Search", "Analysis", "Admin Panel"]
        elif role in ("staff", "adminstaff"):
            pages = ["Home", "Upload", "Collection Manager", "Search", "Analysis"]
        else:
            pages = ["Home", "Upload", "Search", "Analysis"]

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
            current_apikey = st.session_state.get("apikey")
            current_sessionid = st.session_state.get("sessionid")
            authmode = st.session_state.get("authmode")

            if current_apikey and current_sessionid and authmode == "client":
                api_call(
                    "auth/demo/logout",
                    method="POST",
                    apikey=current_apikey,
                    sessionid=current_sessionid,
                    quiet=True,
                )
            elif current_apikey and current_sessionid:
                api_call(
                    "api/v1/ingest/clear-session",
                    method="POST",
                    apikey=current_apikey,
                    sessionid=current_sessionid,
                    quiet=True,
                )

            reset_auth_state()
            st.rerun()

        st.caption(f"Chroma: {CHROMADBPATH}")
        return page


def show_home() -> None:
    render_brand_header(showstickman=True)
    st.markdown("## Home")
    st.write("Upload documents, search indexed material, and run analysis against your legal corpus.")


def show_upload() -> None:
    render_brand_header(showstickman=True)
    role = str(st.session_state.get("role", "client")).lower().strip()
    is_privileged = role in ("admin", "staff", "adminstaff")

    if is_privileged:
        st.markdown("## Upload")
        st.info("Staff and admin can upload into the permanent Chroma database or into a temporary session.")
        destination = st.radio(
            "Upload destination",
            ["Permanent database", "Temporary session"],
            horizontal=True,
            key="uploaddestinationmode",
        )
        collection_mode = st.radio(
            "Collection action",
            ["Create new collection", "Add to existing collection"],
            horizontal=True,
            key="collectionmode",
        )
        if collection_mode == "Create new collection":
            collection_name = st.text_input(
                "New collection name",
                value=st.session_state.get("newcollectionname", ""),
                key="newcollectionname",
                placeholder="e.g. police-disclosure-june-2026",
            ).strip()
        else:
            collection_name = st.text_input(
                "Existing collection name",
                value=st.session_state.get("existingcollectionname", ""),
                key="existingcollectionname",
                placeholder="Enter the target collection name",
            ).strip()
    else:
        st.markdown("## Upload")
        st.info("Client uploads are temporary to this session only.")
        destination = "Temporary session"
        collection_name = "useruploads"

    uploaded_files = st.file_uploader(
        "Select one or more files",
        accept_multiple_files=True,
        type=["txt", "pdf", "docx", "md", "json", "zip"],
        key="uploadfileswidget",
    )

    if uploaded_files:
        st.write("Selected files:")
        for f in uploaded_files:
            st.write(f"- {f.name}")

    upload_button_label = "Upload Files"
    if is_privileged and destination == "Permanent database":
        upload_button_label = "Upload to Permanent Collection"

    if st.button(upload_button_label, type="primary", use_container_width=True, key="btnuploadfiles"):
        if not uploaded_files:
            st.warning("Select at least one file.")
            return

        if is_privileged and destination == "Permanent database" and not collection_name:
            st.warning("Enter a collection name.")
            return

        target_collection = collection_name
        if destination == "Temporary session":
            target_collection = f"temp_{st.session_state.get('sessionid', 'default')}"

        with st.spinner("Uploading and indexing for search and analysis..."):
            if len(uploaded_files) == 1 and uploaded_files[0].name.lower().endswith(".zip"):
                result = api_call(
                    "api/v1/upload/zip",
                    data={"collection": target_collection},
                    method="POST",
                    apikey=st.session_state.get("apikey"),
                    sessionid=st.session_state.get("sessionid"),
                    files=uploaded_files,
                    filefieldname="file",
                )
            else:
                result = api_call(
                    "api/v1/upload/files",
                    data={"collection": target_collection},
                    method="POST",
                    apikey=st.session_state.get("apikey"),
                    sessionid=st.session_state.get("sessionid"),
                    files=uploaded_files,
                )

        if result:
            st.session_state["uploadeddocuments"] = [f.name for f in uploaded_files]
            st.session_state["lastuploadcollection"] = target_collection
            st.session_state["page"] = "Analysis"
            st.success(f"{len(uploaded_files)} files uploaded and indexed successfully into collection {target_collection}")
            st.rerun()


def render_rag_result(result: dict, title: str = "RAG Result") -> None:
    if not isinstance(result, dict):
        st.write(result)
        return

    query = result.get("query")
    answer = result.get("answer")
    executive_summary = result.get("executive_summary")
    confidence = result.get("confidence")
    analysis_type = result.get("analysis_type") or result.get("analysisType")
    confidence_breakdown = result.get("confidence_breakdown")
    audit_report = result.get("audit_report")
    strategic_notes = result.get("strategic_notes")
    sources = result.get("sources") or []
    citations = result.get("citations") or []
    agent_trace = result.get("agent_trace") or {}

    st.markdown(f"## {title}")

    topcols = st.columns([2, 1, 1])
    with topcols[0]:
        if query:
            st.info(f"Query: {query}")
    with topcols[1]:
        if analysis_type:
            st.metric("Type", str(analysis_type).replace("_", " ").title())
    with topcols[2]:
        if confidence is not None:
            try:
                st.metric("Confidence", f"{float(confidence):.0%}")
            except Exception:
                st.metric("Confidence", str(confidence))

    if executive_summary:
        st.markdown("### Executive Summary")
        st.write(executive_summary)

    if answer:
        st.markdown("### Legal Analysis")
        st.write(answer)

    if citations:
        st.markdown("### Citations")
        for c in citations:
            st.write(f"- {c}")

    if sources:
        st.markdown("### Retrieved Sources")
        for i, source in enumerate(sources, 1):
            metadata = source.get("metadata") if isinstance(source, dict) else {}
            document = source.get("document") if isinstance(source, dict) else None
            relevance = source.get("relevance", None) if isinstance(source, dict) else None

            source_name = (
                metadata.get("source")
                or metadata.get("title")
                or metadata.get("filename")
                or "Unknown source"
            )
            category = metadata.get("category", "unknown")
            page_number = metadata.get("pagenumber") or metadata.get("page")

            bits = [f"Collection {category}"]
            if page_number:
                bits.append(f"Page {page_number}")
            if relevance is not None:
                try:
                    bits.append(f"Relevance {float(relevance):.1%}")
                except Exception:
                    bits.append(f"Relevance {relevance}")

            with st.expander(f"{i}. {source_name}"):
                st.caption(" • ".join(bits))
                if document:
                    st.write(document)
                if metadata:
                    with st.expander("Source metadata"):
                        st.json(metadata)

    extra_sections = []
    if strategic_notes:
        extra_sections.append(("Strategic Notes", strategic_notes))
    if audit_report:
        extra_sections.append(("Audit Report", audit_report))
    if confidence_breakdown:
        extra_sections.append(("Confidence Breakdown", confidence_breakdown))

    for heading, body in extra_sections:
        with st.expander(heading):
            st.write(body)

    if agent_trace:
        with st.expander("RAG Trace"):
            st.json(agent_trace)


def show_search() -> None:
    render_brand_header(showstickman=True)
    st.markdown("## Search")
    st.info("Ask a legal question in plain English. AEGIS will explain first, then show verified retrieved sources.")

    query = st.text_area("Search query", height=120, key="searchquery")

    if st.button("Run Search", use_container_width=True, key="searchbtn"):
        if not query.strip():
            st.warning("Enter a search query.")
            return

        querytext = query.strip()

        def search_analysis():
            return api_call(
                "api/v1/analyze",
                data={"query": querytext, "analysis_type": "general"},
                method="POST",
                apikey=st.session_state.get("apikey"),
                sessionid=st.session_state.get("sessionid"),
            )

        def search_sources():
            return api_call(
                "api/v1/search",
                data={"query": querytext},
                method="POST",
                apikey=st.session_state.get("apikey"),
                sessionid=st.session_state.get("sessionid"),
            )

        analysis_result = run_with_stickman("Researching and explaining...", search_analysis)
        search_result = run_with_stickman("Loading verified source list...", search_sources)

        if analysis_result and isinstance(analysis_result, dict):
            display_query = analysis_result.get("query", querytext)
            answer = analysis_result.get("answer")
            executive_summary = analysis_result.get("executive_summary")
            confidence = analysis_result.get("confidence")
            citations = analysis_result.get("citations") or []

            headercols = st.columns([3, 1])
            with headercols[0]:
                st.info(f"Question: {display_query}")
            with headercols[1]:
                if confidence is not None:
                    try:
                        st.metric("Confidence", f"{float(confidence):.0%}")
                    except Exception:
                        st.metric("Confidence", str(confidence))

            st.markdown("### Explanation")
            if executive_summary:
                st.write(executive_summary)
            if answer:
                st.write(answer)
            if citations:
                with st.expander("View citations", expanded=False):
                    for c in citations:
                        st.write(f"- {c}")
        elif analysis_result:
            st.write(analysis_result)

        verified_sources = []
        if isinstance(search_result, dict):
            if isinstance(search_result.get("results"), list):
                verified_sources = search_result.get("results")
            elif isinstance(search_result.get("sources"), list):
                verified_sources = search_result.get("sources")
        elif isinstance(search_result, list):
            verified_sources = search_result

        with st.expander(f"View retrieved sources ({len(verified_sources)})", expanded=False):
            if not verified_sources:
                st.caption("No verified sources returned from /api/v1/search.")
            else:
                for i, item in enumerate(verified_sources, 1):
                    if not isinstance(item, dict):
                        with st.expander(f"{i}. Source {i}", expanded=False):
                            st.write(item)
                        continue

                    metadata = item.get("metadata", {}) or {}
                    document = item.get("document") or item.get("text") or item.get("content")
                    relevance = item.get("relevance", None)
                    source_name = (
                        metadata.get("source")
                        or metadata.get("title")
                        or metadata.get("filename")
                        or item.get("source")
                        or item.get("title")
                        or f"Source {i}"
                    )
                    category = metadata.get("category") or item.get("category") or "unknown"
                    page_number = metadata.get("pagenumber") or metadata.get("page") or item.get("pagenumber") or item.get("page")

                    bits = [f"Collection {category}"]
                    if page_number:
                        bits.append(f"Page {page_number}")
                    if relevance is not None:
                        try:
                            bits.append(f"Relevance {float(relevance):.1%}")
                        except Exception:
                            bits.append(f"Relevance {relevance}")

                    with st.expander(f"{i}. {source_name}", expanded=False):
                        st.caption(" • ".join(bits))
                        if document:
                            st.write(document)
                        else:
                            st.caption("No preview text returned for this source.")

                        merged_meta = {}
                        if isinstance(metadata, dict):
                            merged_meta.update(metadata)
                        for k in ("source", "title", "category", "page", "pagenumber", "relevance"):
                            if k in item and k not in merged_meta:
                                merged_meta[k] = item[k]

                        if merged_meta:
                            with st.expander("Source metadata", expanded=False):
                                st.json(merged_meta)


def show_analysis() -> None:
    render_brand_header(showstickman=True)
    st.markdown("## Analysis")

    query = st.text_area("Analysis request", height=160, key="analysisquery")
    analysis_type = st.selectbox(
        "Analysis type",
        ["general", "charge_review", "similar_cases", "element_check"],
        index=0,
        key="analysistype",
    )

    if st.button("Analyze", type="primary", use_container_width=True, key="analyzebtn"):
        if not query.strip():
            st.warning("Enter an analysis request.")
            return

        def run_analysis():
            return api_call(
                "api/v1/analyze",
                data={"query": query.strip(), "analysis_type": analysis_type},
                method="POST",
                apikey=st.session_state.get("apikey"),
                sessionid=st.session_state.get("sessionid"),
                connecttimeout=15,
                readtimeout=180,
            )

        result = run_with_stickman("Analysing legal materials...", run_analysis)
        if result:
            if isinstance(result, dict):
                render_rag_result(result, title="Analysis Result")
            else:
                st.write(result)

    uploaded_docs = st.session_state.get("uploadeddocuments", [])
    if uploaded_docs:
        st.markdown("### Recently uploaded files")
        for name in uploaded_docs:
            st.write(f"- {name}")


def show_admin_panel() -> None:
    if st.session_state.get("role") not in ("admin", "adminstaff"):
        st.error("Access denied.")
        return

    render_brand_header(showstickman=False)
    st.markdown("## Admin Panel")
    st.write("Admin tools go here.")


def main() -> None:
    init_session()
    if not st.session_state.get("apikey"):
        login()
        return

    page = show_sidebar()
    if page == "Home":
        show_home()
    elif page == "Upload":
        show_upload()
    elif page == "Collection Manager":
        st.info("Collection Manager is available in your fuller app build.")
    elif page == "Search":
        show_search()
    elif page == "Analysis":
        show_analysis()
    elif page == "Admin Panel":
        show_admin_panel()


if __name__ == "__main__":
    main()
