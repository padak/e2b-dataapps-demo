#!/usr/bin/env python3
"""
Test Keboola MCP Server via stdio transport.

Uses subprocess to communicate with MCP server using JSON-RPC protocol.
"""

import json
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


def send_request(proc, method: str, params: dict | None = None, req_id: int = 1) -> dict:
    """Send JSON-RPC request and read response."""
    request = {
        "jsonrpc": "2.0",
        "id": req_id,
        "method": method,
        "params": params or {}
    }

    request_str = json.dumps(request) + "\n"
    proc.stdin.write(request_str)
    proc.stdin.flush()

    # Read response
    response_line = proc.stdout.readline()
    if not response_line:
        return {"error": "No response from server"}

    return json.loads(response_line)


def main():
    print("=" * 60)
    print("Keboola MCP Server - STDIO Test")
    print("=" * 60)

    import os
    kbc_url = os.environ.get("KBC_URL", "").replace("/", "").strip()
    kbc_token = os.environ.get("KBC_TOKEN", "").strip()

    if not kbc_token:
        print("ERROR: KBC_TOKEN not set in .env")
        sys.exit(1)

    # Start MCP server
    print("\n1. Starting MCP server (stdio mode)...")
    env = os.environ.copy()
    env["KBC_STORAGE_API_URL"] = "https://connection.keboola.com"
    env["KBC_STORAGE_TOKEN"] = kbc_token

    proc = subprocess.Popen(
        ["uvx", "keboola_mcp_server", "--transport", "stdio"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env
    )

    try:
        # Initialize
        print("\n2. Sending initialize request...")
        init_response = send_request(proc, "initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0"}
        })

        if "error" in init_response:
            print(f"  ERROR: {init_response}")
            return

        print(f"  ✓ Server initialized")
        print(f"  Server info: {init_response.get('result', {}).get('serverInfo', {})}")

        # List tools
        print("\n3. Listing available tools...")
        tools_response = send_request(proc, "tools/list", {}, req_id=2)

        if "result" in tools_response:
            tools = tools_response["result"].get("tools", [])
            print(f"  Found {len(tools)} tools:")
            for tool in tools:
                print(f"    - {tool['name']}: {tool.get('description', '')[:60]}...")
        else:
            print(f"  Response: {tools_response}")

        # Call get_project_info
        print("\n4. Getting project info...")
        project_response = send_request(proc, "tools/call", {
            "name": "get_project_info",
            "arguments": {}
        }, req_id=3)

        if "result" in project_response:
            content = project_response["result"].get("content", [])
            if content:
                text = content[0].get("text", "")
                print(f"  Project info (first 500 chars):\n{text[:500]}")
        else:
            print(f"  Response: {project_response}")

        # List buckets
        print("\n5. Listing buckets...")
        buckets_response = send_request(proc, "tools/call", {
            "name": "list_buckets",
            "arguments": {}
        }, req_id=4)

        if "result" in buckets_response:
            content = buckets_response["result"].get("content", [])
            if content:
                text = content[0].get("text", "")
                print(f"  Buckets:\n{text[:1000]}")
        else:
            print(f"  Response: {buckets_response}")

        # List tables in a bucket
        print("\n6. Listing tables in out.c-amplitude...")
        tables_response = send_request(proc, "tools/call", {
            "name": "list_tables",
            "arguments": {"bucket_id": "out.c-amplitude"}
        }, req_id=5)

        if "result" in tables_response:
            content = tables_response["result"].get("content", [])
            if content:
                text = content[0].get("text", "")
                print(f"  Tables:\n{text[:1000]}")
        else:
            print(f"  Response: {tables_response}")

        print("\n" + "=" * 60)
        print("MCP SERVER TEST COMPLETE!")
        print("=" * 60)

    finally:
        proc.terminate()
        proc.wait()


if __name__ == "__main__":
    main()
