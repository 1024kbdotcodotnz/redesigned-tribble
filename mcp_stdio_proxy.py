#!/usr/bin/env python3
"""
NZ Legal RAG - MCP stdio-to-HTTP proxy
Run this locally to connect Claude Desktop / Cursor to the remote MCP server.

Usage:
    python mcp_stdio_proxy.py [URL]

Default URL: http://localhost:8080/mcp
(Requires SSH tunnel: ./3_connect.sh 69.30.85.79:22020)
"""

import sys
import json
import urllib.request
import urllib.error

DEFAULT_URL = "http://localhost:8080/mcp"


def main():
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL

    def send(req_obj: dict) -> dict:
        data = json.dumps(req_obj).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = resp.read().decode("utf-8")
                # Handle SSE format: event: message\ndata: {...}
                for line in body.splitlines():
                    line = line.strip()
                    if line.startswith("data:"):
                        return json.loads(line[5:].strip())
                # Fallback: try parsing entire body as JSON
                return json.loads(body)
        except urllib.error.HTTPError as e:
            return {
                "jsonrpc": "2.0",
                "id": req_obj.get("id"),
                "error": {"code": -32603, "message": f"HTTP {e.code}: {e.reason}"},
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": req_obj.get("id"),
                "error": {"code": -32603, "message": str(e)},
            }

    # Read initialize first
    line = sys.stdin.readline()
    if not line:
        return

    req = json.loads(line)
    resp = send(req)
    sys.stdout.write(json.dumps(resp) + "\n")
    sys.stdout.flush()

    # Proxy all subsequent messages
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        resp = send(req)
        sys.stdout.write(json.dumps(resp) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
