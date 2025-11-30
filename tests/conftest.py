"""
Pytest configuration and shared fixtures.
"""

import pytest
import tempfile
import asyncio
from pathlib import Path


@pytest.fixture
def temp_sandbox():
    """Create a temporary sandbox directory for testing."""
    with tempfile.TemporaryDirectory(prefix="test-sandbox-") as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
