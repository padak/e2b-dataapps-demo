import logging
import uuid
from datetime import datetime
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .websocket import ConnectionManager

# Load environment variables from .env file
# Look for .env in project root (parent of backend/)
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Pydantic models
class SessionResponse(BaseModel):
    session_id: str
    created_at: str


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    active_sessions: int


# Global connection manager
manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting E2B Data Apps Builder API")
    yield
    logger.info("Shutting down E2B Data Apps Builder API")
    # Cleanup all active connections
    for session_id in list(manager.active_connections.keys()):
        await manager.disconnect(session_id)


# Create FastAPI application
app = FastAPI(
    title="E2B Data Apps Builder API",
    description="Backend API for building and deploying data applications",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",  # Vite default
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.

    Returns:
        HealthResponse with current status and metrics
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        active_sessions=manager.get_session_count()
    )


@app.post("/api/session", response_model=SessionResponse)
async def create_session():
    """
    Create a new session.

    Returns:
        SessionResponse with new session ID and creation timestamp
    """
    try:
        # Generate timestamp-prefixed session ID for chronological sorting
        # Format: YYYYMMDD-HHMMSS-uuid8chars (e.g., 20251128-143052-a1b2c3d4)
        now = datetime.utcnow()
        timestamp_prefix = now.strftime("%Y%m%d-%H%M%S")
        short_uuid = uuid.uuid4().hex[:8]
        session_id = f"{timestamp_prefix}-{short_uuid}"
        created_at = now.isoformat()

        logger.info(f"Created new session: {session_id}")

        return SessionResponse(
            session_id=session_id,
            created_at=created_at
        )

    except Exception as e:
        logger.error(f"Error creating session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create session")


@app.get("/api/sessions")
async def list_sessions():
    """
    List all active sessions.

    Returns:
        List of active session IDs
    """
    try:
        return {
            "sessions": manager.get_active_sessions(),
            "count": manager.get_session_count(),
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error listing sessions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list sessions")


@app.get("/api/session/{session_id}/status")
async def get_session_status(session_id: str):
    """
    Check if a session exists and is active.

    Returns:
        Session status and whether it can be reconnected to
    """
    try:
        is_active = session_id in manager.active_connections
        has_agent = session_id in manager.agents

        return {
            "session_id": session_id,
            "is_active": is_active,
            "has_agent": has_agent,
            "can_reconnect": has_agent,  # Can reconnect if agent still exists
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error checking session status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to check session status")


@app.websocket("/ws/chat/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str, reconnect: bool = False):
    """
    WebSocket endpoint for real-time chat communication.

    Args:
        websocket: WebSocket connection
        session_id: Unique session identifier
        reconnect: If True, try to reconnect to existing session/agent

    The WebSocket accepts JSON messages with the following format:
    {
        "type": "chat" | "ping" | "reset",
        "message": "user message (for chat type)"
    }

    And sends responses in the format:
    {
        "type": "connection" | "chat_received" | "agent_message" | "error" | "pong",
        "message": "response content",
        ...additional fields
    }
    """
    try:
        # Connect and initialize (or reconnect to existing agent)
        await manager.connect(websocket, session_id, reconnect=reconnect)

        logger.info(f"WebSocket connection established: {session_id}")

        # Main message loop
        while True:
            try:
                # Receive JSON data from client
                data = await websocket.receive_json()

                # Process the message
                await manager.handle_message(session_id, data)

            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected normally: {session_id}")
                break

            except RuntimeError as e:
                # WebSocket disconnected unexpectedly
                logger.warning(f"WebSocket runtime error for {session_id}: {e}")
                break

            except Exception as e:
                logger.error(f"Error in message loop for {session_id}: {e}", exc_info=True)
                # Try to send error to client, then always break (C3 fix)
                try:
                    await manager.send_message(session_id, {
                        "type": "error",
                        "message": "Internal server error processing message"
                    })
                except Exception:
                    logger.warning(f"Failed to send error to {session_id}")
                # Always break after error to prevent resource waste
                break

    except Exception as e:
        logger.error(f"Error in WebSocket endpoint for {session_id}: {e}", exc_info=True)

    finally:
        # Cleanup on exit - keep agent alive for 5 minutes for potential reconnect
        # Agent will be fully cleaned up on explicit reset or session timeout
        await manager.disconnect(session_id, keep_agent=True)
        logger.info(f"WebSocket connection closed: {session_id} (agent kept for reconnect)")


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "E2B Data Apps Builder API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "create_session": "POST /api/session",
            "list_sessions": "/api/sessions",
            "websocket": "/ws/chat/{session_id}"
        },
        "docs": "/docs",
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
