#!/usr/bin/env python3
"""
Shared authentication UI for NZ Legal Platform demo.

Supports:
- Admin / Staff password login
- Demo visitor OTP flow
- Single shared access form
"""

import os
import requests
import streamlit as st

try:
    API_URL = os.environ.get("API_URL") or st.secrets["API_URL"]
except Exception:
    API_URL = os.environ.get("API_URL", "http://127.0.0.1:8000")


def init_auth_state():
    defaults = {
        "auth": {
            "is_authenticated": False,
            "role": None,
            "session_id": None,
            "display_name": None,
            "contact_id": None,
            "access_token": None,
        },
        "pending_demo": {
            "challenge_id": None,
            "email": "",
            "phone": "",
            "access_code": None,
        },
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def set_auth_session(payload: dict):
    st.session_state.auth = {
        "is_authenticated": True,
        "role": payload.get("role"),
        "session_id": payload.get("session_id"),
        "display_name": payload.get("display_name"),
        "contact_id": payload.get("contact_id"),
        "access_token": payload.get("access_token"),
    }

    st.session_state.api_key = payload.get("access_token")
    st.session_state.session_id = payload.get("session_id")
    st.session_state.tenant_info = {
        "name": payload.get("display_name", "User"),
        "role": payload.get("role", "demo"),
    }


def clear_auth_session():
    st.session_state.auth = {
        "is_authenticated": False,
        "role": None,
        "session_id": None,
        "display_name": None,
        "contact_id": None,
        "access_token": None,
    }
    st.session_state.pending_demo = {
        "challenge_id": None,
        "email": "",
        "phone": "",
        "access_code": None,
    }

    st.session_state.api_key = None
    st.session_state.session_id = None
    st.session_state.tenant_info = None


def api_post(path: str, payload: dict):
    url = f"{API_URL}{path}"
    response = requests.post(url, json=payload, timeout=20)
    try:
        data = response.json()
    except Exception:
        data = {"ok": False, "detail": f"HTTP {response.status_code}"}

    if response.status_code >= 400:
        data.setdefault("ok", False)
        data.setdefault("detail", f"HTTP {response.status_code}")

    return data


def render_access_form():
    init_auth_state()

    st.markdown('<div class="auth-shell">', unsafe_allow_html=True)
    st.markdown('<div class="auth-hero">', unsafe_allow_html=True)
    st.markdown("## Secure Access")
    st.caption("Verified temporary access for demo users. Admin and Staff use the same form.")
    st.markdown("</div>", unsafe_allow_html=True)

    access_type = st.radio(
        "Access type",
        ["Visitor demo", "Staff / Admin"],
        horizontal=True,
        key="access_type",
        label_visibility="visible",
    )

    if access_type == "Staff / Admin":
        st.markdown('<div class="auth-panel">', unsafe_allow_html=True)
        with st.form("staff_login_form", clear_on_submit=False):
            st.markdown("### Staff sign in")
            st.caption("Use your staff or admin credentials to enter the workspace.")
            identifier = st.text_input("Username or email", key="login_identifier")
            password = st.text_input("Password", type="password", key="login_password")
            submitted = st.form_submit_button("Sign in", use_container_width=True)

            if submitted:
                result = api_post("/auth/staff-login", {
                    "identifier": identifier.strip(),
                    "password": password,
                })

                if result.get("ok"):
                    set_auth_session(result)
                    st.success("Login successful.")
                    st.rerun()
                else:
                    st.error(result.get("detail", "Login failed."))
        st.markdown("</div>", unsafe_allow_html=True)

    else:
        st.markdown('<div class="auth-panel">', unsafe_allow_html=True)
        if not st.session_state.pending_demo.get("challenge_id"):
            with st.form("demo_start_form", clear_on_submit=False):
                st.markdown("### Demo access")
                st.caption("Request a one-time code for temporary evaluation access.")
                email = st.text_input("Work email", key="demo_email")
                phone = st.text_input("Mobile number", key="demo_phone")
                submitted = st.form_submit_button("Send access code", use_container_width=True)

                if submitted:
                    result = api_post("/auth/demo/start", {
                        "email": email.strip(),
                        "phone": phone.strip(),
                    })

                    if result.get("ok"):
                        st.session_state.pending_demo = {
                            "challenge_id": result["challenge_id"],
                            "email": email.strip(),
                            "phone": phone.strip(),
                            "access_code": result.get("access_code"),
                        }
                        st.success("One-time access code generated.")
                        st.rerun()
                    else:
                        st.error(result.get("detail", "Could not start access session."))
        else:
            pending = st.session_state.pending_demo

            with st.form("demo_verify_form", clear_on_submit=False):
                st.markdown("### Verify code")
                st.caption("Confirm the one-time access code to enter the demo workspace.")
                st.text_input("Work email", value=pending["email"], disabled=True, key="demo_email_locked")
                st.text_input("Mobile number", value=pending["phone"], disabled=True, key="demo_phone_locked")

                if pending.get("access_code"):
                    st.info(
                        f"Demo access code: {pending['access_code']}\n\n"
                        "Shown on-screen for demonstration purposes only."
                    )

                otp_code = st.text_input("One-time access code", key="demo_otp")
                submitted = st.form_submit_button("Verify and enter", use_container_width=True)

                if submitted:
                    result = api_post("/auth/demo/verify", {
                        "challenge_id": pending["challenge_id"],
                        "email": pending["email"],
                        "phone": pending["phone"],
                        "access_code": otp_code.strip(),
                    })

                    if result.get("ok"):
                        set_auth_session(result)
                        st.session_state.pending_demo = {
                            "challenge_id": None,
                            "email": "",
                            "phone": "",
                            "access_code": None,
                        }
                        st.success("Access granted.")
                        st.rerun()
                    else:
                        st.error(result.get("detail", "Verification failed."))

            if st.button("Start over", use_container_width=True, key="demo_start_over"):
                st.session_state.pending_demo = {
                    "challenge_id": None,
                    "email": "",
                    "phone": "",
                    "access_code": None,
                }
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


def is_authenticated() -> bool:
    init_auth_state()
    return bool(st.session_state.auth.get("is_authenticated"))


def get_current_role() -> str:
    init_auth_state()
    return st.session_state.auth.get("role") or "guest"


def logout_button():
    init_auth_state()
    if st.button("Sign Out", use_container_width=True, key="auth_logout"):
        token = st.session_state.auth.get("access_token")
        if token:
            try:
                requests.post(
                    f"{API_URL}/auth/logout",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10,
                )
            except Exception:
                pass

        clear_auth_session()
        st.rerun()