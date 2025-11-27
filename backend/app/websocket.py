import logging
from typing import Dict
from fastapi import WebSocket
import json

from .agent import AppBuilderAgent

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and their associated agents."""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.agents: Dict[str, AppBuilderAgent] = {}
        logger.info("ConnectionManager initialized")

    async def connect(self, websocket: WebSocket, session_id: str):
        """
        Accept a WebSocket connection and create an associated agent.

        Args:
            websocket: The WebSocket connection to accept
            session_id: Unique identifier for this session
        """
        try:
            await websocket.accept()
            self.active_connections[session_id] = websocket

            # Create and initialize a new agent for this session
            agent = AppBuilderAgent()
            await agent.initialize()
            self.agents[session_id] = agent

            logger.info(f"Client connected: session_id={session_id}")

            # Send welcome message
            await self.send_message(session_id, {
                "type": "connection",
                "status": "connected",
                "session_id": session_id,
                "message": "Connected to app builder"
            })

        except Exception as e:
            logger.error(f"Error connecting client {session_id}: {e}", exc_info=True)
            raise

    async def disconnect(self, session_id: str):
        """
        Clean up connection and agent resources.

        Args:
            session_id: Session identifier to disconnect
        """
        try:
            # Clean up agent
            if session_id in self.agents:
                agent = self.agents[session_id]
                await agent.cleanup()
                del self.agents[session_id]
                logger.info(f"Agent cleaned up for session: {session_id}")

            # Remove connection
            if session_id in self.active_connections:
                del self.active_connections[session_id]
                logger.info(f"Client disconnected: session_id={session_id}")

        except Exception as e:
            logger.error(f"Error disconnecting client {session_id}: {e}", exc_info=True)

    async def send_message(self, session_id: str, message: dict):
        """
        Send a JSON message to a specific client.

        Args:
            session_id: Target session identifier
            message: Dictionary to send as JSON
        """
        try:
            if session_id in self.active_connections:
                websocket = self.active_connections[session_id]
                await websocket.send_json(message)
            else:
                logger.warning(f"Attempted to send message to non-existent session: {session_id}")

        except Exception as e:
            logger.error(f"Error sending message to {session_id}: {e}", exc_info=True)
            # Connection might be broken, clean up
            await self.disconnect(session_id)

    async def handle_message(self, session_id: str, data: dict):
        """
        Process incoming message and stream agent responses.

        Args:
            session_id: Session identifier
            data: Received message data
        """
        try:
            logger.info(f"Received message from {session_id}: {data.get('type', 'unknown')}")

            # Get the agent for this session
            agent = self.agents.get(session_id)
            if not agent:
                logger.error(f"No agent found for session: {session_id}")
                await self.send_message(session_id, {
                    "type": "error",
                    "message": "Session not initialized"
                })
                return

            message_type = data.get("type")

            if message_type == "chat":
                # Handle chat message
                user_message = data.get("message", "")
                if not user_message:
                    await self.send_message(session_id, {
                        "type": "error",
                        "message": "Empty message received"
                    })
                    return

                # Send acknowledgment
                await self.send_message(session_id, {
                    "type": "chat_received",
                    "message": user_message
                })

                # Stream agent response using chat() method
                async for event in agent.chat(user_message):
                    await self.send_message(session_id, event)

            elif message_type == "ping":
                # Handle ping/keepalive
                await self.send_message(session_id, {
                    "type": "pong"
                })

            elif message_type == "reset":
                # Reset the agent by cleaning up and reinitializing
                await agent.cleanup()
                await agent.initialize()
                await self.send_message(session_id, {
                    "type": "reset_complete",
                    "message": "Session reset successfully"
                })

            else:
                logger.warning(f"Unknown message type from {session_id}: {message_type}")
                await self.send_message(session_id, {
                    "type": "error",
                    "message": f"Unknown message type: {message_type}"
                })

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from {session_id}: {e}", exc_info=True)
            await self.send_message(session_id, {
                "type": "error",
                "message": "Invalid JSON format"
            })

        except Exception as e:
            logger.error(f"Error handling message from {session_id}: {e}", exc_info=True)
            await self.send_message(session_id, {
                "type": "error",
                "message": f"Internal error: {str(e)}"
            })

    def get_active_sessions(self) -> list:
        """Get list of active session IDs."""
        return list(self.active_connections.keys())

    def get_session_count(self) -> int:
        """Get count of active sessions."""
        return len(self.active_connections)
