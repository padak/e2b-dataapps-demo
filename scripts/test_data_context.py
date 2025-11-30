#!/usr/bin/env python3
"""
Test script for Phase 4: Data Context Injection.

Tests:
1. DataContext loading from environment
2. Credentials to env dict conversion
3. .env.local file generation
4. Integration with LocalSandboxManager
"""

import os
import sys
import tempfile
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from dotenv import load_dotenv

# Load .env from project root
load_dotenv(Path(__file__).parent.parent / ".env")

from app.context.data_context import (
    DataContext,
    KeboolaCredentials,
    get_keboola_credentials,
    inject_credentials_to_env,
    get_credentials_status,
)


def test_data_context_loading():
    """Test that DataContext loads credentials from environment."""
    print("\n=== Test 1: DataContext Loading ===")

    context = DataContext()

    print(f"Has Keboola credentials: {context.has_keboola_credentials}")

    if context.keboola_credentials:
        creds = context.keboola_credentials
        print(f"  KBC_URL: {creds.kbc_url}")
        print(f"  WORKSPACE_ID: {creds.workspace_id}")
        print(f"  BRANCH_ID: {creds.branch_id}")
        print(f"  Token: {'*' * 10} (hidden)")
        print(f"  Is valid: {creds.is_valid}")
    else:
        print("  No credentials found!")
        print("  Make sure .env contains KBC_URL, KBC_TOKEN, WORKSPACE_ID, BRANCH_ID")

    return context.has_keboola_credentials


def test_credentials_conversion():
    """Test conversion to env dict and export commands."""
    print("\n=== Test 2: Credentials Conversion ===")

    creds = get_keboola_credentials()

    if not creds:
        print("  Skipped - no credentials available")
        return False

    # Test to_env_dict
    env_dict = creds.to_env_dict()
    print(f"  Environment dict keys: {list(env_dict.keys())}")

    # Test to_export_commands
    export_cmds = creds.to_export_commands()
    print(f"  Export commands generated ({len(export_cmds)} chars)")

    # Verify all required keys
    required_keys = ["KBC_URL", "KBC_TOKEN", "WORKSPACE_ID", "BRANCH_ID"]
    missing = [k for k in required_keys if k not in env_dict]

    if missing:
        print(f"  WARNING: Missing keys: {missing}")
        return False

    print("  All required keys present!")
    return True


def test_env_file_generation():
    """Test .env.local file generation."""
    print("\n=== Test 3: .env.local Generation ===")

    creds = get_keboola_credentials()

    if not creds:
        print("  Skipped - no credentials available")
        return False

    # Create temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Inject credentials
        env_file = inject_credentials_to_env(tmppath, creds)

        print(f"  Created: {env_file}")
        print(f"  Exists: {env_file.exists()}")

        # Read and verify content
        content = env_file.read_text()
        print(f"  Content lines: {len(content.splitlines())}")

        # Check content has required vars
        for key in ["KBC_URL", "KBC_TOKEN", "WORKSPACE_ID", "BRANCH_ID"]:
            if key not in content:
                print(f"  ERROR: Missing {key} in .env.local")
                return False

        print("  .env.local content verified!")

        # Show sanitized content (hide token)
        print("\n  Content preview:")
        for line in content.splitlines():
            if line.startswith("KBC_TOKEN="):
                print("    KBC_TOKEN=***hidden***")
            else:
                print(f"    {line}")

    return True


def test_credentials_status():
    """Test credentials status API."""
    print("\n=== Test 4: Credentials Status ===")

    status = get_credentials_status()

    print(f"  Keboola configured: {status['keboola']['configured']}")
    print(f"  Keboola URL: {status['keboola']['url']}")
    print(f"  Workspace ID: {status['keboola']['workspace_id']}")
    print(f"  Branch ID: {status['keboola']['branch_id']}")

    return status['keboola']['configured']


async def test_sandbox_integration():
    """Test integration with LocalSandboxManager."""
    print("\n=== Test 5: Sandbox Integration ===")

    # Import here to avoid circular imports
    from app.local_sandbox_manager import LocalSandboxManager

    manager = LocalSandboxManager(session_id="test_data_context")

    try:
        # Initialize sandbox
        sandbox_path = await manager.ensure_sandbox()
        print(f"  Sandbox path: {sandbox_path}")

        # Check if _inject_credentials method exists
        if hasattr(manager, '_inject_credentials'):
            result = await manager._inject_credentials(sandbox_path)
            print(f"  Credentials injected: {result}")

            if result:
                env_file = sandbox_path / ".env.local"
                if env_file.exists():
                    print(f"  .env.local exists: {env_file}")
                    return True
                else:
                    print("  ERROR: .env.local not created")
                    return False
        else:
            print("  ERROR: _inject_credentials method not found")
            return False

    finally:
        await manager.destroy(delete_files=True)


def main():
    """Run all tests."""
    print("=" * 60)
    print("Phase 4: Data Context Injection - Test Suite")
    print("=" * 60)

    # Check environment
    print("\nEnvironment check:")
    env_vars = ["KBC_URL", "KBC_TOKEN", "WORKSPACE_ID", "BRANCH_ID"]
    for var in env_vars:
        value = os.getenv(var)
        if value:
            display = value[:20] + "..." if len(value) > 20 else value
            if "TOKEN" in var:
                display = "***set***"
            print(f"  {var}: {display}")
        else:
            print(f"  {var}: NOT SET")

    # Run tests
    results = []

    results.append(("DataContext Loading", test_data_context_loading()))
    results.append(("Credentials Conversion", test_credentials_conversion()))
    results.append(("Env File Generation", test_env_file_generation()))
    results.append(("Credentials Status", test_credentials_status()))

    # Async test
    import asyncio
    results.append(("Sandbox Integration", asyncio.run(test_sandbox_integration())))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = 0
    failed = 0
    for name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"  {name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1

    print(f"\nTotal: {passed} passed, {failed} failed")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
