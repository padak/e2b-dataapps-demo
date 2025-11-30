"""
Factory for creating sandbox managers based on configuration.
"""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def create_sandbox_manager(session_id: Optional[str] = None):
    """
    Create appropriate sandbox manager based on SANDBOX_MODE env variable.

    Args:
        session_id: Session ID for logging context

    Returns:
        SandboxManager or LocalSandboxManager instance
    """
    mode = os.getenv("SANDBOX_MODE", "local").lower()

    if mode == "e2b":
        from .sandbox_manager import SandboxManager
        logger.info(f"[{session_id}] Creating E2B SandboxManager")
        return SandboxManager(session_id=session_id)
    else:
        from .local_sandbox_manager import LocalSandboxManager
        logger.info(f"[{session_id}] Creating LocalSandboxManager")
        return LocalSandboxManager(session_id=session_id)
