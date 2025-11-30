#!/usr/bin/env python3
"""
Explore Keboola MCP Server tools.

Prerequisites:
1. Start MCP server: uvx keboola_mcp_server --transport sse --port 8001
2. Set env vars: KBC_STORAGE_API_URL, KBC_STORAGE_TOKEN

This script uses the MCP SSE client to call tools.
"""

import asyncio
import json
import sys
from contextlib import asynccontextmanager

import httpx


class KeboolaMCPClient:
    """Simple client for Keboola MCP Server via SSE."""

    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.session_id: str | None = None

    async def connect(self) -> str:
        """Connect to SSE endpoint and get session ID."""
        async with httpx.AsyncClient() as client:
            async with client.stream("GET", f"{self.base_url}/sse") as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if "session_id=" in data:
                            # Extract session_id from URL like /sse/messages/?session_id=xxx
                            self.session_id = data.split("session_id=")[1]
                            return self.session_id
        raise RuntimeError("Could not get session ID from MCP server")

    async def call_tool(self, tool_name: str, arguments: dict | None = None) -> dict:
        """Call an MCP tool and return the result."""
        if not self.session_id:
            await self.connect()

        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments or {}
            }
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/sse/messages/?session_id={self.session_id}",
                json=message,
                headers={"Content-Type": "application/json"}
            )

            # The response comes via SSE, we need to read it
            # For simplicity, let's try direct HTTP endpoint
            if response.status_code == 202:
                # Need to read from SSE stream
                return {"status": "accepted", "note": "Response will come via SSE stream"}

            return response.json()

    async def list_tools(self) -> list[dict]:
        """List available MCP tools."""
        if not self.session_id:
            await self.connect()

        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/sse/messages/?session_id={self.session_id}",
                json=message,
                headers={"Content-Type": "application/json"}
            )
            return {"status_code": response.status_code, "text": response.text[:500]}


async def test_mcp_connection():
    """Test basic MCP server connectivity."""
    print("=" * 60)
    print("Keboola MCP Server - Exploration")
    print("=" * 60)

    # Check if server is running
    print("\n1. Checking MCP server...")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:8001/")
            print(f"  Server response: {response.status_code}")
    except Exception as e:
        print(f"  ERROR: Server not reachable: {e}")
        print("  Please start the server with:")
        print("    export KBC_STORAGE_API_URL=https://connection.keboola.com")
        print("    export KBC_STORAGE_TOKEN=your_token")
        print("    uvx keboola_mcp_server --transport sse --port 8001")
        sys.exit(1)

    # Try to connect
    print("\n2. Connecting to SSE endpoint...")
    client = KeboolaMCPClient()
    try:
        session_id = await client.connect()
        print(f"  ✓ Connected! Session ID: {session_id[:20]}...")
    except Exception as e:
        print(f"  ERROR: Could not connect: {e}")
        sys.exit(1)

    # Try to list tools
    print("\n3. Listing available tools...")
    try:
        result = await client.list_tools()
        print(f"  Response: {result}")
    except Exception as e:
        print(f"  Note: {e}")

    print("\n" + "=" * 60)
    print("MCP SERVER IS RUNNING!")
    print("=" * 60)
    print("""
To use with Claude Agent SDK, add to your MCP config:

{
  "mcpServers": {
    "keboola": {
      "command": "uvx",
      "args": ["keboola_mcp_server", "--transport", "stdio"],
      "env": {
        "KBC_STORAGE_API_URL": "https://connection.keboola.com",
        "KBC_STORAGE_TOKEN": "your_token"
      }
    }
  }
}

Available tools (from server logs):
- get_project_info - Project information
- list_buckets - List storage buckets
- list_tables - List tables in bucket
- get_table - Table schema/details
- query_data - Execute SQL query
- search - Search for tables/buckets
- find_component_id - Find component by name
- docs_query - Query documentation
""")


if __name__ == "__main__":
    asyncio.run(test_mcp_connection())
