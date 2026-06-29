#!/usr/bin/env python3
"""
Patch server.py get_current_demo_or_tenant auth fallback.
Run: python /workspace/nz_legal_rag/patch_auth.py
"""

import sys
from pathlib import Path

SERVER_PATH = Path("/workspace/nz_legal_rag/api/server.py")
BACKUP_PATH = Path("/workspace/nz_legal_rag/api/server.py.bak.auth")

def patch():
    if not SERVER_PATH.exists():
        print(f"ERROR: {SERVER_PATH} not found")
        sys.exit(1)
    
    # Backup
    BACKUP_PATH.write_text(SERVER_PATH.read_text(), encoding="utf-8")
    print(f"Backup saved to {BACKUP_PATH}")
    
    content = SERVER_PATH.read_text(encoding="utf-8")
    
    # Find the old try block inside get_current_demo_or_tenant
    old_block = """    try:
        # Try passing the credentials object first (some implementations expect this)
        tenant = new_auth_get_current_tenant(credentials)
        if tenant:
            return tenant
    except Exception:
        pass
    
    try:
        # Fallback: try with raw token string
        tenant = new_auth_get_current_tenant(token)
        if tenant:
            return tenant
    except Exception:
        pass"""
    
    new_block = """    try:
        # Try passing the credentials object first (some implementations expect this)
        tenant = new_auth_get_current_tenant(credentials)
        if tenant is not None:
            return tenant
    except HTTPException:
        # New auth explicitly rejected this token - don't fallback, re-raise
        raise
    except Exception:
        pass
    
    try:
        # Fallback: try with raw token string
        tenant = new_auth_get_current_tenant(token)
        if tenant is not None:
            return tenant
    except HTTPException:
        raise
    except Exception:
        pass"""
    
    if old_block in content:
        content = content.replace(old_block, new_block)
        print("Patched get_current_demo_or_tenant auth fallback")
    else:
        print("WARNING: Could not find exact old block")
        sys.exit(1)
    
    # Write
    SERVER_PATH.write_text(content, encoding="utf-8")
    print(f"\nSUCCESS: Patched {SERVER_PATH}")

if __name__ == "__main__":
    patch()
