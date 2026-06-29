#!/usr/bin/env python3
"""
patch_demo_anonymous_fixed.py
Safely patch api/server.py so demo username is not derived from email.
"""
from pathlib import Path

SERVER_PATH = Path("api/server.py")

if not SERVER_PATH.exists():
    print(f"ERROR: {SERVER_PATH} not found")
    raise SystemExit(1)

text = SERVER_PATH.read_text()

old_line = '        "username": request.email.strip().split("@")[0].replace(".", "_").replace(" ", "_")[:24] or f"guest_{str(uuid4())[:8]}",'
new_line = '        "username": f"guest_{str(uuid4())[:8]}",'

if old_line in text:
    text = text.replace(old_line, new_line, 1)
    SERVER_PATH.write_text(text)
    print("✓ Patched: demo username now uses random guest id")
else:
    print("⚠ Exact target line not found; no changes written")
