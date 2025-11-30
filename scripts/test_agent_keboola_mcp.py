#!/usr/bin/env python3
"""
Test Keboola MCP integration in the AppBuilderAgent.

This script tests that the agent can use Keboola MCP tools to explore data.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from dotenv import load_dotenv

# Load environment
load_dotenv(Path(__file__).parent.parent / ".env")


async def test_keboola_mcp_integration():
    """Test that Keboola MCP tools are available and working."""
    print("=" * 60)
    print("Testing Keboola MCP Integration in AppBuilderAgent")
    print("=" * 60)

    # Check environment
    print("\n1. Checking environment...")
    from app.integrations.keboola_mcp import is_keboola_configured, get_keboola_mcp_config

    if not is_keboola_configured():
        print("  ERROR: Keboola not configured. Set KBC_URL and KBC_TOKEN.")
        return False

    config = get_keboola_mcp_config()
    print(f"  ✓ Keboola MCP configured")
    print(f"  Command: {config['command']} {' '.join(config['args'])}")

    # Test agent initialization
    print("\n2. Testing agent initialization...")
    from app.agent import AppBuilderAgent

    agent = AppBuilderAgent(session_id="test_keboola_mcp")

    try:
        await agent.initialize()
        print("  ✓ Agent initialized successfully")

        # Check if Keboola tools are in allowed_tools
        if agent.client and hasattr(agent.client, '_options'):
            allowed = agent.client._options.allowed_tools or []
            keboola_tools = [t for t in allowed if "keboola" in t]
            print(f"  ✓ Found {len(keboola_tools)} Keboola tools in allowed_tools")
            for tool in keboola_tools[:5]:
                print(f"    - {tool}")
            if len(keboola_tools) > 5:
                print(f"    ... and {len(keboola_tools) - 5} more")

        # Test a simple query that uses Keboola MCP
        print("\n3. Testing Keboola MCP query (list_buckets)...")
        print("  Sending query to agent: 'List the available Keboola buckets'")

        response_text = []
        tool_calls = []

        async for event in agent.chat("Use the Keboola MCP tools to list available buckets. Just list the bucket names."):
            if event["type"] == "text":
                response_text.append(event["content"])
            elif event["type"] == "tool_use":
                tool_calls.append(event["tool"])
                print(f"  Tool called: {event['tool']}")
            elif event["type"] == "done":
                print("  ✓ Query completed")

        # Check if Keboola tools were used
        keboola_calls = [t for t in tool_calls if "keboola" in t.lower()]
        if keboola_calls:
            print(f"  ✓ Keboola MCP tools were called: {keboola_calls}")
        else:
            print(f"  ⚠ No Keboola tools called (tools used: {tool_calls})")

        # Print response excerpt
        full_response = "".join(response_text)
        if full_response:
            print(f"\n  Response excerpt:")
            print(f"  {full_response[:500]}...")

        print("\n" + "=" * 60)
        print("TEST COMPLETE!")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        await agent.cleanup()


if __name__ == "__main__":
    success = asyncio.run(test_keboola_mcp_integration())
    sys.exit(0 if success else 1)
