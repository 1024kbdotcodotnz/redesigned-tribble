from pathlib import Path

path = Path("/workspace/nz_legal_rag/api/server.py")
text = path.read_text()

text = text.replace(
    '    username: str\n',
    '',
    1
)

text = text.replace(
    '        "username": rec["username"],\n',
    '',
    1
)

path.write_text(text)
print("patched", path)
