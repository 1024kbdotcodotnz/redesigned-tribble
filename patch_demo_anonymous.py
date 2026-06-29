#!/usr/bin/env python3
"""
patch_demo_anonymous.py
Patch api/server.py to make the demo login truly anonymous:
  - username becomes a random guest_<uuid> instead of email-derived
"""
import re
from pathlib import Path

SERVER_PATH = Path("api/server.py")

if not SERVER_PATH.exists():
    print(f"ERROR: {SERVER_PATH} not found")
    exit(1)

text = SERVER_PATH.read_text()

# Fix username derivation in demo_start
old_pattern = r'"username":\s*request\.email\.strip\(\)\.split\("@")\[0\].replace\([^)]+\).replace\([^)]+\)[:24]\s*or\s*f"guest_{str(uuid4())[:8]}",'
new_username_line = '"username": f"guest_{str(uuid4())[:8]}",'

if re.search(old_pattern, text):
    text = re.sub(old_pattern, new_username_line, text)
    print("✓ Patched: username is now random guest_<uuid>")
else:
    simple_old = r'"username":\s*request\.email\.strip\(\)\.split\("@")\[0\][^,]+,'
    if re.search(simple_old, text):
        text = re.sub(simple_old, new_username_line + "\n", text, flags=re.S)
        print("✓ Patched: username is now random guest_<uuid> (simpler pattern)")
    else:
        print("⚠ Could not find the old username line; skipping username patch.")

SERVER_PATH.write_text(text)
print(f"✓ Patch written to {SERVER_PATH}")
