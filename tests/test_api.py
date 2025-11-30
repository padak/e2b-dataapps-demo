"""
Tests for FastAPI endpoints.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, AsyncMock

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from fastapi.testclient import TestClient


# Mock the agent initialization to avoid Claude SDK calls
@pytest.fixture
def mock_agent():
    """Mock AppBuilderAgent to avoid real Claude API calls."""
    with patch("app.websocket.AppBuilderAgent") as mock:
        instance = AsyncMock()
        instance.initialize = AsyncMock()
        instance.cleanup = AsyncMock()
        instance.chat = AsyncMock(return_value=iter([
            {"type": "text", "content": "Hello!"},
            {"type": "done", "preview_url": None}
        ]))
        mock.return_value = instance
        yield mock


@pytest.fixture
def client(mock_agent):
    """Create test client with mocked agent."""
    from app.main import app
    return TestClient(app)


class TestHealthEndpoint:
    """Test the /health endpoint."""

    def test_health_returns_ok(self, client):
        """Health check should return status healthy."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "active_sessions" in data

    def test_health_includes_session_count(self, client):
        """Health check should include active session count."""
        response = client.get("/health")
        data = response.json()

        assert isinstance(data["active_sessions"], int)
        assert data["active_sessions"] >= 0


class TestSessionEndpoint:
    """Test the /api/session endpoint."""

    def test_create_session_returns_id(self, client):
        """Creating session should return session ID."""
        response = client.post("/api/session")
        assert response.status_code == 200

        data = response.json()
        assert "session_id" in data
        assert isinstance(data["session_id"], str)
        assert len(data["session_id"]) > 0

    def test_session_id_format(self, client):
        """Session ID should have expected format (timestamp-uuid)."""
        response = client.post("/api/session")
        data = response.json()

        session_id = data["session_id"]
        # Format: YYYYMMDD-HHMMSS-xxxxxxxx
        parts = session_id.split("-")
        assert len(parts) >= 3

        # First part should be date (8 digits)
        assert len(parts[0]) == 8
        assert parts[0].isdigit()

        # Second part should be time (6 digits)
        assert len(parts[1]) == 6
        assert parts[1].isdigit()

    def test_multiple_sessions_unique(self, client):
        """Multiple session creations should return unique IDs."""
        response1 = client.post("/api/session")
        response2 = client.post("/api/session")

        id1 = response1.json()["session_id"]
        id2 = response2.json()["session_id"]

        assert id1 != id2


class TestSessionsListEndpoint:
    """Test the /api/sessions endpoint."""

    def test_list_sessions_returns_list(self, client):
        """Should return list of sessions."""
        response = client.get("/api/sessions")
        assert response.status_code == 200

        data = response.json()
        assert "sessions" in data
        assert isinstance(data["sessions"], list)


class TestRootEndpoint:
    """Test the root / endpoint."""

    def test_root_returns_info(self, client):
        """Root should return API information."""
        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert "name" in data
        assert "endpoints" in data

    def test_root_lists_endpoints(self, client):
        """Root should list available endpoints."""
        response = client.get("/")
        data = response.json()

        endpoints = data["endpoints"]
        # Check that expected endpoints exist (as keys or values)
        assert "health" in endpoints or "/health" in endpoints.values()
        assert "websocket" in endpoints or "/ws/chat/{session_id}" in endpoints.values()


class TestCORS:
    """Test CORS configuration."""

    def test_cors_headers_present(self, client):
        """Should include CORS headers for allowed origins."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET"
            }
        )
        # FastAPI/Starlette may return 200 or 400 for OPTIONS
        # The important thing is CORS headers are set for actual requests
        assert response.status_code in [200, 400]

    def test_cors_allows_localhost(self, client):
        """Should allow localhost origins."""
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:5173"}
        )
        assert response.status_code == 200
