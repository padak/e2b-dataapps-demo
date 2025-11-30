import asyncio
import logging
from typing import Dict, Optional
from fastapi import WebSocket
import json

from .agent import AppBuilderAgent
from .logging_config import get_session_logger, close_session_logger

logger = logging.getLogger(__name__)

# Default timeout for agent responses (10 minutes)
# Security reviewer + complex apps can take longer
AGENT_RESPONSE_TIMEOUT = 600

# Grace period before destroying agent after disconnect (60 seconds)
# Allows page reloads and short disconnects without losing session
AGENT_CLEANUP_GRACE_PERIOD = 60


class ConnectionManager:
    """Manages WebSocket connections and their associated agents."""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.agents: Dict[str, AppBuilderAgent] = {}
        # Locks for thread-safe operations (C2 fix)
        self._connection_lock = asyncio.Lock()
        self._send_locks: Dict[str, asyncio.Lock] = {}  # Per-session send locks (M1 fix)
        self._chat_in_progress: Dict[str, bool] = {}  # Track active chats (H2 fix)
        # Pending cleanup tasks for graceful agent destruction
        self._pending_cleanups: Dict[str, asyncio.Task] = {}
        logger.info("ConnectionManager initialized")

    async def connect(self, websocket: WebSocket, session_id: str, reconnect: bool = False):
        """
        Accept a WebSocket connection and create or reuse an associated agent.

        Args:
            websocket: The WebSocket connection to accept
            session_id: Unique identifier for this session
            reconnect: If True, try to reuse existing agent instead of creating new one
        """
        try:
            # Get session logger and log connection start
            session_logger = get_session_logger(session_id)
            session_logger.log_session("WS_CONNECT", f"client connecting (reconnect={reconnect})")

            # Cancel any pending cleanup for this session
            if session_id in self._pending_cleanups:
                cleanup_task = self._pending_cleanups[session_id]
                if not cleanup_task.done():
                    cleanup_task.cancel()
                    logger.info(f"[{session_id}] Cancelled pending cleanup - client reconnecting")
                del self._pending_cleanups[session_id]

            # Check if we can reconnect to existing agent
            existing_agent = self.agents.get(session_id)
            is_reconnecting = reconnect and existing_agent is not None

            if is_reconnecting:
                agent = existing_agent
                logger.info(f"[{session_id}] Reconnecting to existing agent")
            else:
                # Initialize new agent BEFORE accepting WebSocket (H3 fix)
                agent = AppBuilderAgent(session_id=session_id)
                await agent.initialize()

            # Now accept the connection
            await websocket.accept()

            async with self._connection_lock:
                # Close existing websocket if any (but keep the agent)
                if session_id in self.active_connections:
                    try:
                        old_ws = self.active_connections[session_id]
                        await old_ws.close()
                    except Exception:
                        pass  # Old connection might already be dead

                self.active_connections[session_id] = websocket
                self.agents[session_id] = agent
                if session_id not in self._send_locks:
                    self._send_locks[session_id] = asyncio.Lock()
                if session_id not in self._chat_in_progress:
                    self._chat_in_progress[session_id] = False

            logger.info(f"[{session_id}] Client {'reconnected' if is_reconnecting else 'connected'}")
            session_logger.log_session("WS_CONNECTED", f"client {'reconnected' if is_reconnecting else 'connected'}")

            # Send welcome message with reconnect status
            await self.send_message(session_id, {
                "type": "connection",
                "status": "connected",
                "session_id": session_id,
                "reconnected": is_reconnecting,
                "message": "Reconnected to existing session" if is_reconnecting else "Connected to app builder"
            })

        except Exception as e:
            logger.error(f"[{session_id}] Error connecting client: {e}", exc_info=True)
            raise

    async def disconnect(self, session_id: str, keep_agent: bool = False):
        """
        Clean up connection and optionally schedule agent cleanup with grace period.

        Args:
            session_id: Session identifier to disconnect
            keep_agent: If True, schedules agent cleanup after grace period instead of immediate cleanup
        """
        try:
            async with self._connection_lock:
                # Remove connection
                if session_id in self.active_connections:
                    del self.active_connections[session_id]
                    logger.info(f"[{session_id}] Client disconnected (agent_kept={keep_agent})")

                if keep_agent:
                    # Schedule cleanup after grace period
                    if session_id not in self._pending_cleanups:
                        cleanup_task = asyncio.create_task(
                            self._delayed_cleanup(session_id, AGENT_CLEANUP_GRACE_PERIOD)
                        )
                        self._pending_cleanups[session_id] = cleanup_task
                        logger.info(f"[{session_id}] Scheduled agent cleanup in {AGENT_CLEANUP_GRACE_PERIOD}s")
                    else:
                        logger.debug(f"[{session_id}] Cleanup already scheduled")
                else:
                    # Immediate cleanup
                    await self._cleanup_agent(session_id)

        except Exception as e:
            logger.error(f"[{session_id}] Error disconnecting client: {e}", exc_info=True)

    async def _delayed_cleanup(self, session_id: str, delay: int):
        """
        Wait for grace period, then cleanup agent if client hasn't reconnected.

        Args:
            session_id: Session to cleanup
            delay: Delay in seconds before cleanup
        """
        try:
            logger.info(f"[{session_id}] Grace period started ({delay}s)")
            await asyncio.sleep(delay)

            # Check if client reconnected during grace period
            if session_id in self.active_connections:
                logger.info(f"[{session_id}] Client reconnected during grace period - cleanup cancelled")
                return

            logger.info(f"[{session_id}] Grace period expired - cleaning up agent")
            await self._cleanup_agent(session_id)

            # Remove from pending cleanups
            async with self._connection_lock:
                self._pending_cleanups.pop(session_id, None)

        except asyncio.CancelledError:
            logger.info(f"[{session_id}] Cleanup cancelled - client reconnected")
        except Exception as e:
            logger.error(f"[{session_id}] Error in delayed cleanup: {e}", exc_info=True)

    async def _cleanup_agent(self, session_id: str):
        """
        Perform actual agent cleanup.

        Args:
            session_id: Session to cleanup
        """
        async with self._connection_lock:
            # Clean up agent
            if session_id in self.agents:
                agent = self.agents[session_id]
                try:
                    await agent.cleanup()
                except Exception as cleanup_error:
                    logger.warning(f"[{session_id}] Error during agent cleanup: {cleanup_error}")
                del self.agents[session_id]
                logger.info(f"[{session_id}] Agent cleaned up")

            # Clean up session-specific resources
            self._send_locks.pop(session_id, None)
            self._chat_in_progress.pop(session_id, None)

            # Close session logger
            close_session_logger(session_id)

    async def send_message(self, session_id: str, message: dict):
        """
        Send a JSON message to a specific client.
        Uses per-session lock to ensure message ordering (M1 fix).

        Args:
            session_id: Target session identifier
            message: Dictionary to send as JSON
        """
        try:
            # Get send lock for this session (without holding connection_lock)
            send_lock = self._send_locks.get(session_id)
            if not send_lock:
                logger.warning(f"[{session_id}] Attempted to send message to non-existent session")
                return

            # Log outgoing WebSocket message
            session_logger = get_session_logger(session_id)
            session_logger.log_ws_out(message)

            async with send_lock:
                if session_id in self.active_connections:
                    websocket = self.active_connections[session_id]
                    await websocket.send_json(message)
                else:
                    logger.warning(f"[{session_id}] Connection closed during send")

        except Exception as e:
            logger.error(f"[{session_id}] Error sending message: {e}", exc_info=True)
            # Connection might be broken, clean up
            await self.disconnect(session_id)

    async def handle_message(self, session_id: str, data: dict):
        """
        Process incoming message and stream agent responses.
        Includes timeout protection (H1) and reset during streaming protection (H2).

        Args:
            session_id: Session identifier
            data: Received message data
        """
        try:
            # Log incoming WebSocket message
            session_logger = get_session_logger(session_id)
            session_logger.log_ws_in(data)

            logger.info(f"[{session_id}] Received message: type={data.get('type', 'unknown')}")

            # Get the agent for this session
            agent = self.agents.get(session_id)
            if not agent:
                logger.error(f"[{session_id}] No agent found for session")
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

                # Check if another chat is in progress
                if self._chat_in_progress.get(session_id, False):
                    logger.warning(f"[{session_id}] Chat already in progress, ignoring message")
                    await self.send_message(session_id, {
                        "type": "error",
                        "message": "Please wait for current response to complete"
                    })
                    return

                # Send acknowledgment
                await self.send_message(session_id, {
                    "type": "chat_received",
                    "message": user_message
                })

                # Mark chat as in progress (H2 fix)
                self._chat_in_progress[session_id] = True

                try:
                    # Stream agent response with timeout (H1 fix)
                    async with asyncio.timeout(AGENT_RESPONSE_TIMEOUT):
                        async for event in agent.chat(user_message):
                            await self.send_message(session_id, event)
                except asyncio.TimeoutError:
                    logger.error(f"[{session_id}] Agent response timed out after {AGENT_RESPONSE_TIMEOUT}s")
                    await self.send_message(session_id, {
                        "type": "error",
                        "message": f"Response timed out after {AGENT_RESPONSE_TIMEOUT} seconds"
                    })
                finally:
                    # Always clear chat in progress flag
                    self._chat_in_progress[session_id] = False

            elif message_type == "ping":
                # Handle ping/keepalive
                await self.send_message(session_id, {
                    "type": "pong"
                })

            elif message_type == "reset":
                # Check if chat is in progress (H2 fix)
                if self._chat_in_progress.get(session_id, False):
                    logger.warning(f"[{session_id}] Cannot reset during active chat")
                    await self.send_message(session_id, {
                        "type": "error",
                        "message": "Cannot reset while a response is in progress"
                    })
                    return

                # Reset the agent by cleaning up and reinitializing
                try:
                    await agent.cleanup()
                    await agent.initialize()
                    await self.send_message(session_id, {
                        "type": "reset_complete",
                        "message": "Session reset successfully"
                    })
                except Exception as reset_error:
                    logger.error(f"[{session_id}] Reset failed: {reset_error}", exc_info=True)
                    await self.send_message(session_id, {
                        "type": "error",
                        "message": f"Reset failed: {str(reset_error)}"
                    })

            else:
                logger.warning(f"[{session_id}] Unknown message type: {message_type}")
                await self.send_message(session_id, {
                    "type": "error",
                    "message": f"Unknown message type: {message_type}"
                })

        except json.JSONDecodeError as e:
            logger.error(f"[{session_id}] Invalid JSON: {e}", exc_info=True)
            await self.send_message(session_id, {
                "type": "error",
                "message": "Invalid JSON format"
            })

        except Exception as e:
            logger.error(f"[{session_id}] Error handling message: {e}", exc_info=True)
            # Reset chat in progress flag on error
            self._chat_in_progress[session_id] = False
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
