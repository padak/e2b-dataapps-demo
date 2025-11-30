#!/usr/bin/env python3
"""
Test script for Security Reviewer functionality.

Tests:
1. Security review state management
2. Hook blocking before review
3. Hook allowing after review passes
4. State reset on code change
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.app.security.security_review import (
    _security_review_state,
    mark_security_review_completed,
    reset_security_review,
    get_security_review_state,
)

from backend.app.agent import (
    require_security_review,
    invalidate_security_review_on_code_change,
)


def test_security_review_state():
    """Test security review state management."""
    print("\n=== Test: Security Review State Management ===")

    session_id = "test_session_1"

    # Initially no state
    assert session_id not in _security_review_state
    print("✓ Initial state is empty")

    # Mark as completed and passed
    mark_security_review_completed(session_id, passed=True, issues_summary="No issues found")
    assert _security_review_state[session_id]["security_review_completed"] == True
    assert _security_review_state[session_id]["security_review_passed"] == True
    print("✓ State updated correctly for passed review")

    # Reset state
    reset_security_review(session_id)
    assert session_id not in _security_review_state
    print("✓ State reset correctly")

    # Mark as completed but failed
    mark_security_review_completed(session_id, passed=False, issues_summary="SQL injection found")
    assert _security_review_state[session_id]["security_review_completed"] == True
    assert _security_review_state[session_id]["security_review_passed"] == False
    assert "SQL injection" in _security_review_state[session_id]["issues_summary"]
    print("✓ State updated correctly for failed review")

    # Cleanup
    reset_security_review(session_id)
    print("✓ Cleanup complete")


async def test_require_security_review_hook():
    """Test the PreToolUse hook that requires security review."""
    print("\n=== Test: Require Security Review Hook ===")

    session_id = "test_session_2"
    context = {"session_id": session_id}

    # Test 1: Non-dev-server tool should pass through
    result = await require_security_review(
        {"tool_name": "Write"},
        None,
        context
    )
    assert result == {}
    print("✓ Non-dev-server tool passes through")

    # Test 2: Dev server without review should be blocked
    result = await require_security_review(
        {"tool_name": "mcp__e2b__sandbox_start_dev_server"},
        None,
        context
    )
    assert result.get("decision") == "block"
    assert "Security Review Required" in result.get("reason", "")
    print("✓ Dev server blocked when no review done")

    # Test 3: After review passes, dev server should be allowed
    mark_security_review_completed(session_id, passed=True, issues_summary="Safe")
    result = await require_security_review(
        {"tool_name": "mcp__e2b__sandbox_start_dev_server"},
        None,
        context
    )
    assert result == {}
    print("✓ Dev server allowed after review passes")

    # Test 4: After review fails, dev server should be blocked
    mark_security_review_completed(session_id, passed=False, issues_summary="Found SQL injection")
    result = await require_security_review(
        {"tool_name": "mcp__e2b__sandbox_start_dev_server"},
        None,
        context
    )
    assert result.get("decision") == "block"
    assert "Fixes Required" in result.get("reason", "")
    print("✓ Dev server blocked when review fails")

    # Cleanup
    reset_security_review(session_id)
    print("✓ Cleanup complete")


async def test_invalidate_on_code_change():
    """Test the PostToolUse hook that invalidates review on code change."""
    print("\n=== Test: Invalidate on Code Change ===")

    session_id = "test_session_3"
    context = {"session_id": session_id}

    # Test 1: No invalidation if no review completed
    result = await invalidate_security_review_on_code_change(
        {"tool_name": "Write"},
        None,
        context
    )
    assert result == {}
    print("✓ No invalidation when no review exists")

    # Test 2: Invalidation when review was completed
    mark_security_review_completed(session_id, passed=True, issues_summary="Safe")
    result = await invalidate_security_review_on_code_change(
        {"tool_name": "Edit"},
        None,
        context
    )
    assert "systemMessage" in result
    assert "Security Review Invalidated" in result["systemMessage"]
    assert session_id not in _security_review_state
    print("✓ Review invalidated when code changes")

    # Test 3: Read tool should not invalidate
    mark_security_review_completed(session_id, passed=True, issues_summary="Safe")
    result = await invalidate_security_review_on_code_change(
        {"tool_name": "Read"},
        None,
        context
    )
    assert result == {}
    assert session_id in _security_review_state
    print("✓ Read tool does not invalidate review")

    # Cleanup
    reset_security_review(session_id)
    print("✓ Cleanup complete")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Security Reviewer Tests")
    print("=" * 60)

    try:
        test_security_review_state()
        await test_require_security_review_hook()
        await test_invalidate_on_code_change()

        print("\n" + "=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
        return 0
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
