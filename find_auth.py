from pathlib import Path
import re

files = [
    Path("logs/streamlit.log"),
    Path("logs/api.log"),
]

patterns = {
    "api_key": re.compile(r"api[_-]?key\s*[:=]\s*([A-Za-z0-9_\-\.]+)", re.I),
    "session_id": re.compile(r"session[_-]?id\s*[:=]\s*([A-Za-z0-9_\-\.]+)", re.I),
    "bearer": re.compile(r"Bearer\s+([A-Za-z0-9_\-\.]+)"),
}

for f in files:
    if not f.exists():
        continue
    text = f.read_text(errors="ignore")
    print(f"== {f} ==")
    found_any = False
    for name, pat in patterns.items():
        vals = sorted(set(pat.findall(text)))
        if vals:
            found_any = True
            print(name, vals[:20])
    if not found_any:
        print("No token/session matches found.")