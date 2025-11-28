"""
Super Logging Configuration for App Builder.

Provides session-scoped logging with multiple outputs:
- session.log: Main timeline
- websocket.log: WS traffic
- agent.log: Agent events
- llm_requests.jsonl: Raw LLM requests
- llm_responses.jsonl: Raw LLM responses
- tool_calls.jsonl: Tool executions
- sandbox.log: Sandbox operations
- errors.log: All errors aggregated
"""

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

# Base logs directory
LOGS_BASE_DIR = Path(__file__).parent.parent.parent / "logs"


class SessionLogger:
    """Session-scoped logger that writes to multiple files."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.session_dir = LOGS_BASE_DIR / session_id
        self.session_dir.mkdir(parents=True, exist_ok=True)

        self.start_time = datetime.now(timezone.utc)
        self._lock = threading.Lock()

        # Open log files
        self._session_log = open(self.session_dir / "session.log", "a")
        self._websocket_log = open(self.session_dir / "websocket.log", "a")
        self._agent_log = open(self.session_dir / "agent.log", "a")
        self._llm_requests = open(self.session_dir / "llm_requests.jsonl", "a")
        self._llm_responses = open(self.session_dir / "llm_responses.jsonl", "a")
        self._tool_calls = open(self.session_dir / "tool_calls.jsonl", "a")
        self._sandbox_log = open(self.session_dir / "sandbox.log", "a")
        self._errors_log = open(self.session_dir / "errors.log", "a")

        # Token counters
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.request_count = 0
        self.tool_call_count = 0

        self.log_session("SESSION_START", f"session_id={session_id}")

    def _timestamp(self) -> str:
        """Return current UTC timestamp in ISO format."""
        return datetime.now(timezone.utc).isoformat()

    def _write(self, file, tag: str, message: str):
        """Write a tagged log line to a file (thread-safe)."""
        with self._lock:
            line = f"[{self._timestamp()}] [{tag}] {message}\n"
            file.write(line)
            file.flush()

    def _write_json(self, file, data: dict):
        """Write a JSON line to a file (thread-safe)."""
        with self._lock:
            data["timestamp"] = self._timestamp()
            file.write(json.dumps(data) + "\n")
            file.flush()

    # Session log methods
    def log_session(self, tag: str, message: str):
        """Log to main session timeline."""
        self._write(self._session_log, tag, message)

    # WebSocket log methods
    def log_ws_in(self, data: dict):
        """Log incoming WebSocket message."""
        self._write(self._websocket_log, "IN", json.dumps(data))
        self.log_session("WS_IN", f"type={data.get('type', 'unknown')}")

    def log_ws_out(self, data: dict):
        """Log outgoing WebSocket message."""
        self._write(self._websocket_log, "OUT", json.dumps(data))
        self.log_session("WS_OUT", f"type={data.get('type', 'unknown')}")

    # Agent log methods
    def log_agent(self, tag: str, message: str):
        """Log agent event (also logs to session timeline)."""
        self._write(self._agent_log, tag, message)
        self.log_session(f"AGENT_{tag}", message)

    # LLM request/response logging
    def log_llm_request(
        self,
        msg_id: str,
        system_prompt_len: int,
        messages: list,
        tools: list,
        model: str,
    ):
        """Log LLM request details."""
        self.request_count += 1
        data = {
            "msg_id": msg_id,
            "system_prompt_len": system_prompt_len,
            "message_count": len(messages),
            "messages_preview": self._truncate_messages(messages),
            "tools": tools,
            "model": model,
        }
        self._write_json(self._llm_requests, data)
        self.log_session(
            "LLM_REQUEST", f"msg_id={msg_id}, system_len={system_prompt_len}"
        )

    def log_llm_response(
        self,
        msg_id: str,
        stop_reason: str,
        input_tokens: int,
        output_tokens: int,
        content_blocks: list,
    ):
        """Log LLM response details and update token counters."""
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        data = {
            "msg_id": msg_id,
            "stop_reason": stop_reason,
            "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
            "content_blocks_count": len(content_blocks),
            "content_blocks_summary": self._summarize_blocks(content_blocks),
        }
        self._write_json(self._llm_responses, data)
        self.log_session(
            "LLM_RESPONSE",
            f"msg_id={msg_id}, tokens_in={input_tokens}, tokens_out={output_tokens}",
        )

    # Tool call logging
    def log_tool_call(
        self,
        tool_id: str,
        tool_name: str,
        input_data: dict,
        duration_ms: float,
        success: bool,
        output: Any,
    ):
        """Log tool call execution details."""
        self.tool_call_count += 1
        data = {
            "tool_id": tool_id,
            "tool_name": tool_name,
            "input": self._sanitize_input(input_data),
            "duration_ms": duration_ms,
            "success": success,
            "output_summary": self._summarize_output(output),
        }
        self._write_json(self._tool_calls, data)
        self.log_session(
            "TOOL_CALL",
            f"tool={tool_name}, success={success}, duration={duration_ms:.0f}ms",
        )

    # Sandbox log methods
    def log_sandbox(self, tag: str, message: str):
        """Log sandbox operation (also logs to session timeline)."""
        self._write(self._sandbox_log, tag, message)
        self.log_session(f"SANDBOX_{tag}", message)

    # Error logging
    def log_error(
        self, component: str, error: str, traceback: Optional[str] = None
    ):
        """Log error with optional traceback."""
        self._write(self._errors_log, component, error)
        if traceback:
            self._write(self._errors_log, "TRACEBACK", traceback)
        self.log_session("ERROR", f"[{component}] {error[:100]}")

    # Helper methods
    def _truncate_messages(self, messages: list) -> list:
        """Truncate message content for logging (last 3 messages only)."""
        result = []
        for msg in messages[-3:]:  # Last 3 messages only
            content = msg.get("content", "")
            if isinstance(content, str) and len(content) > 200:
                content = content[:200] + "..."
            result.append(
                {"role": msg.get("role"), "content_len": len(str(content))}
            )
        return result

    def _summarize_blocks(self, blocks: list) -> list:
        """Summarize content blocks for logging."""
        result = []
        for block in blocks:
            block_type = block.get("type", "unknown")
            if block_type == "text":
                text = block.get("text", "")
                result.append(
                    {
                        "type": "text",
                        "len": len(text),
                        "preview": text[:100] + "..." if len(text) > 100 else text,
                    }
                )
            elif block_type == "tool_use":
                result.append(
                    {
                        "type": "tool_use",
                        "name": block.get("name"),
                        "id": block.get("id"),
                    }
                )
            elif block_type == "tool_result":
                result.append(
                    {"type": "tool_result", "tool_use_id": block.get("tool_use_id")}
                )
            else:
                result.append({"type": block_type})
        return result

    def _sanitize_input(self, input_data: dict) -> dict:
        """Sanitize tool input for logging (truncate large content)."""
        result = {}
        for key, value in input_data.items():
            if key == "content" and isinstance(value, str) and len(value) > 500:
                result[key] = f"<{len(value)} bytes>"
            else:
                result[key] = value
        return result

    def _summarize_output(self, output: Any) -> Any:
        """Summarize tool output for logging (truncate large strings)."""
        if isinstance(output, dict):
            return {
                k: (
                    f"<{len(str(v))} chars>"
                    if isinstance(v, str) and len(str(v)) > 200
                    else v
                )
                for k, v in output.items()
            }
        elif isinstance(output, str) and len(output) > 200:
            return f"<{len(output)} chars>"
        return output

    def close(self):
        """Close all log files and write final summary."""
        duration = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        self.log_session(
            "SESSION_END",
            f"duration={duration:.1f}s, requests={self.request_count}, "
            f"tools={self.tool_call_count}, tokens_in={self.total_input_tokens}, "
            f"tokens_out={self.total_output_tokens}",
        )

        for f in [
            self._session_log,
            self._websocket_log,
            self._agent_log,
            self._llm_requests,
            self._llm_responses,
            self._tool_calls,
            self._sandbox_log,
            self._errors_log,
        ]:
            f.close()


# Global registry of session loggers
_session_loggers: Dict[str, SessionLogger] = {}
_registry_lock = threading.Lock()


def get_session_logger(session_id: str) -> SessionLogger:
    """Get or create a session logger for the given session ID."""
    with _registry_lock:
        if session_id not in _session_loggers:
            _session_loggers[session_id] = SessionLogger(session_id)
        return _session_loggers[session_id]


def close_session_logger(session_id: str):
    """Close and remove a session logger."""
    with _registry_lock:
        if session_id in _session_loggers:
            _session_loggers[session_id].close()
            del _session_loggers[session_id]
