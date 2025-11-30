"""
Security Review State Management.

Tracks security review status per session to enforce security checks
before starting the dev server.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Track security review state per session
_security_review_state: dict[str, dict] = {}


def mark_security_review_completed(session_id: str, passed: bool, issues_summary: str = "") -> None:
    """
    Mark security review as completed for a session.

    Called by the agent after running security-reviewer subagent.

    Args:
        session_id: The session ID
        passed: True if review passed (safe=true, no high severity issues)
        issues_summary: Summary of issues found (if any)
    """
    _security_review_state[session_id] = {
        "security_review_completed": True,
        "security_review_passed": passed,
        "issues_summary": issues_summary,
    }
    logger.info(f"[SECURITY] Session {session_id}: Review completed, passed={passed}")


def reset_security_review(session_id: str) -> None:
    """Reset security review state for a session (e.g., after code changes)."""
    if session_id in _security_review_state:
        del _security_review_state[session_id]
        logger.info(f"[SECURITY] Session {session_id}: Review state reset")


def get_security_review_state(session_id: str) -> dict:
    """
    Get the security review state for a session.

    Returns:
        dict with keys:
        - security_review_completed: bool
        - security_review_passed: bool
        - issues_summary: str
        Returns empty dict if no state exists.
    """
    return _security_review_state.get(session_id, {})


def is_security_review_passed(session_id: str) -> bool:
    """
    Check if security review passed for a session.

    Returns:
        True if review was completed AND passed, False otherwise.
    """
    state = _security_review_state.get(session_id, {})
    return (
        state.get("security_review_completed", False) and
        state.get("security_review_passed", False)
    )
