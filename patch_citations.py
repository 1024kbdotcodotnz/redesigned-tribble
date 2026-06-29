#!/usr/bin/env python3
# Patch streamlit_app.py for inline citations
import sys
from pathlib import Path

APP_PATH = Path("/workspace/nz_legal_rag/web/streamlit_app.py")
BACKUP = Path("/workspace/nz_legal_rag/web/streamlit_app.py.bak.citations")

def patch():
    if not APP_PATH.exists():
        print(f"ERROR: {APP_PATH} not found")
        sys.exit(1)
    
    BACKUP.write_text(APP_PATH.read_text(), encoding="utf-8")
    print(f"Backup: {BACKUP}")
    
    content = APP_PATH.read_text(encoding="utf-8")
    
    # 1. Update answer display with inline citations
    old = "    answer = result.get(\"answer\") or result.get(\"analysis\") or result.get(\"response\")\n    if answer:\n        st.markdown(answer)"
    new = "    answer = result.get(\"answer\") or result.get(\"analysis\") or result.get(\"response\")\n    if answer:\n        import re\n        highlighted = re.sub(\n            r'\\[Source\\s*(\\d+)\\]',\n            r'<span style=\"background:#c5a88033; padding:2px 6px; border-radius:4px; font-size:0.85em; color:#c5a880;\">[Source \1]</span>',\n            answer\n        )\n        st.markdown(highlighted, unsafe_allow_html=True)"
    if old in content:
        content = content.replace(old, new)
        print("Updated answer display")
    else:
        print("WARNING: Could not find answer block")
    
    # 2. Update sources display with styled badges
    old = "    sources = result.get(\"sources\") or result.get(\"results\") or []\n    if sources:\n        st.markdown(\"#### Retrieved Sources\")\n        for index, source in enumerate(sources, 1):\n            if not isinstance(source, dict):\n                st.markdown(f\"{index}. Source {index}\")\n                continue\n\n            metadata = source.get(\"metadata\") or {}\n            document = source.get(\"document\") or source.get(\"content\") or source.get(\"text\") or \"\"\n            sourcename = resolve_source_name(source, index)\n            page = metadata.get(\"page\") or metadata.get(\"pagenumber\") or source.get(\"page\") or source.get(\"pagenumber\")\n\n            if page:\n                st.markdown(f\"{index}. {sourcename} (page {page})\")\n            else:\n                st.markdown(f\"{index}. {sourcename}\")\n\n            if document:\n                with st.expander(f\"Excerpt {index}\"):\n                    st.write(document)"
    new = "    sources = result.get(\"sources\") or result.get(\"results\") or []\n    if sources:\n        st.markdown(\"#### 📚 Verified Sources\")\n        for index, source in enumerate(sources, 1):\n            if not isinstance(source, dict):\n                st.markdown(f\"{index}. Source {index}\")\n                continue\n\n            metadata = source.get(\"metadata\") or {}\n            document = source.get(\"document\") or source.get(\"content\") or source.get(\"text\") or \"\"\n            sourcename = resolve_source_name(source, index)\n            page = metadata.get(\"page\") or metadata.get(\"pagenumber\") or source.get(\"page\") or source.get(\"pagenumber\")\n            relevance = source.get(\"relevance\", None)\n            category = metadata.get(\"category\") or source.get(\"category\") or \"unknown\"\n\n            rel_badge = f\"<span style='font-size:0.75em; color:#888;'> relevance {relevance:.1%}</span>\" if relevance is not None else \"\"\n            page_str = f\" (p. {page})\" if page else \"\"\n            st.markdown(\n                f\"<div style='margin:8px 0; padding:8px 12px; background:#1f1e21; border-left:3px solid #c5a880; border-radius:0 6px 6px 0;'>\"\n                f\"<strong style='color:#c5a880;'>[{index}]</strong> {sourcename}{page_str}{rel_badge}\"\n                f\"<span style='font-size:0.8em; color:#666; float:right;'>{category}</span>\"\n                f\"</div>\",\n                unsafe_allow_html=True\n            )\n\n            if document:\n                with st.expander(\"Excerpt\"):\n                    st.markdown(f\"<div style='color:#ccc; font-size:0.92em; line-height:1.6;'>{document}</div>\", unsafe_allow_html=True)"
    if old in content:
        content = content.replace(old, new)
        print("Updated sources display")
    else:
        print("WARNING: Could not find sources block")
    
    APP_PATH.write_text(content, encoding="utf-8")
    print(f"\nSUCCESS: Patched {APP_PATH}")

if __name__ == "__main__":
    patch()
