"""
E2B Sandbox MCP Tools for Claude Agent SDK

Provides tools for interacting with E2B sandboxes through the Claude Agent SDK MCP server.
These tools allow Claude to manage files, run commands, and interact with sandboxes.
"""

import logging
import time
import traceback
from contextvars import ContextVar
from typing import Any, Optional

from claude_agent_sdk import tool, create_sdk_mcp_server
from ..logging_config import get_session_logger

# Configure logging
logger = logging.getLogger(__name__)

# Session-local sandbox manager using contextvars
# This ensures each async context (session) has its own sandbox manager
_sandbox_manager: ContextVar[Optional[Any]] = ContextVar('sandbox_manager', default=None)
_session_id: ContextVar[Optional[str]] = ContextVar('session_id', default=None)


def set_sandbox_manager(manager):
    """Set the sandbox manager for the current session context."""
    _sandbox_manager.set(manager)
    logger.info("Sandbox manager set for current session context")


def set_session_id(session_id: str):
    """Set the session ID for the current session context."""
    _session_id.set(session_id)
    logger.info(f"Session ID set for current session context: {session_id}")


def get_session_id() -> Optional[str]:
    """Get the session ID for the current session context."""
    return _session_id.get()


def get_manager():
    """Get the sandbox manager for the current session context."""
    manager = _sandbox_manager.get()
    if manager is None:
        logger.error("Sandbox manager not initialized when tool was called")
        raise RuntimeError("Sandbox manager not initialized. Call set_sandbox_manager first.")
    return manager


def clear_sandbox_manager():
    """Clear the sandbox manager for the current session context."""
    _sandbox_manager.set(None)
    logger.debug("Sandbox manager cleared for current session context")


@tool(
    "sandbox_write_file",
    "Write or create a file in the E2B sandbox. Use this to create new files or overwrite existing files with content.",
    {"file_path": str, "content": str}
)
async def sandbox_write_file(args: dict[str, Any]) -> dict[str, Any]:
    """
    Write content to a file in the sandbox filesystem.

    Args:
        file_path: The absolute path where the file should be written (e.g., '/home/user/app.py')
        content: The text content to write to the file

    Returns:
        Success message with the file path, or error details
    """
    start_time = time.time()
    session_id = get_session_id()
    slogger = get_session_logger(session_id) if session_id else None
    tool_id = f"tool_{int(start_time*1000)}"

    file_path = args.get("file_path", "unknown")
    content_len = len(args.get("content", ""))
    logger.info(f"[TOOL] sandbox_write_file called: path={file_path}, content_size={content_len} bytes")

    try:
        content = args["content"]

        manager = get_manager()
        result = await manager.write_file(file_path, content)

        duration_ms = (time.time() - start_time) * 1000
        logger.info(f"[TOOL] sandbox_write_file success: {file_path} ({result['size']} bytes)")

        if slogger:
            slogger.log_tool_call(
                tool_id=tool_id,
                tool_name="sandbox_write_file",
                input_data=args,
                duration_ms=duration_ms,
                success=True,
                output=result
            )

        return {
            "content": [{
                "type": "text",
                "text": f"Successfully wrote {result['size']} bytes to {file_path}"
            }]
        }
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(f"[TOOL] sandbox_write_file failed: {file_path} - {e}", exc_info=True)

        if slogger:
            slogger.log_tool_call(
                tool_id=tool_id,
                tool_name="sandbox_write_file",
                input_data=args,
                duration_ms=duration_ms,
                success=False,
                output=str(e)
            )
            slogger.log_error("sandbox_write_file", str(e), traceback.format_exc())

        return {
            "content": [{
                "type": "text",
                "text": f"Error writing file: {str(e)}"
            }],
            "isError": True
        }


@tool(
    "sandbox_read_file",
    "Read the contents of a file from the E2B sandbox. Use this to inspect files that exist in the sandbox.",
    {"file_path": str}
)
async def sandbox_read_file(args: dict[str, Any]) -> dict[str, Any]:
    """
    Read content from a file in the sandbox filesystem.

    Args:
        file_path: The absolute path of the file to read (e.g., '/home/user/app.py')

    Returns:
        The file content, or error details if the file doesn't exist
    """
    start_time = time.time()
    session_id = get_session_id()
    slogger = get_session_logger(session_id) if session_id else None
    tool_id = f"tool_{int(start_time*1000)}"

    file_path = args.get("file_path", "unknown")
    logger.info(f"[TOOL] sandbox_read_file called: path={file_path}")

    try:
        manager = get_manager()
        content = await manager.read_file(file_path)

        duration_ms = (time.time() - start_time) * 1000
        logger.info(f"[TOOL] sandbox_read_file success: {file_path} ({len(content)} bytes)")

        if slogger:
            slogger.log_tool_call(
                tool_id=tool_id,
                tool_name="sandbox_read_file",
                input_data=args,
                duration_ms=duration_ms,
                success=True,
                output={"size": len(content)}
            )

        return {
            "content": [{
                "type": "text",
                "text": f"File: {file_path}\n\n{content}"
            }]
        }
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(f"[TOOL] sandbox_read_file failed: {file_path} - {e}", exc_info=True)

        if slogger:
            slogger.log_tool_call(
                tool_id=tool_id,
                tool_name="sandbox_read_file",
                input_data=args,
                duration_ms=duration_ms,
                success=False,
                output=str(e)
            )
            slogger.log_error("sandbox_read_file", str(e), traceback.format_exc())

        return {
            "content": [{
                "type": "text",
                "text": f"Error reading file: {str(e)}"
            }],
            "isError": True
        }


@tool(
    "sandbox_run_command",
    "Execute a shell command in the E2B sandbox. Use this to run bash commands, npm, yarn, or any CLI tools. Returns stdout, stderr, and exit code. Use timeout parameter for long-running commands (default 120s, max 600s). For dev servers, use sandbox_start_dev_server instead.",
    {"command": str, "timeout": int}
)
async def sandbox_run_command(args: dict[str, Any]) -> dict[str, Any]:
    """
    Execute a shell command in the sandbox.

    Args:
        command: The shell command to execute (e.g., 'npm install', 'npm run build')
        timeout: Command timeout in seconds (default: 120, max: 600). Use 0 for no timeout.

    Returns:
        The command output (stdout and stderr), exit code, and any errors
    """
    start_time = time.time()
    session_id = get_session_id()
    slogger = get_session_logger(session_id) if session_id else None
    tool_id = f"tool_{int(start_time*1000)}"

    command = args.get("command", "")
    timeout = args.get("timeout", 120)

    # Validate and cap timeout
    if timeout < 0:
        timeout = 120
    elif timeout > 600:
        timeout = 600
        logger.warning(f"[TOOL] sandbox_run_command: timeout capped to 600s (requested: {args.get('timeout')})")

    logger.info(f"[TOOL] sandbox_run_command called: cmd='{command[:80]}{'...' if len(command) > 80 else ''}', timeout={timeout}s")

    try:
        manager = get_manager()
        result = await manager.run_command(command, timeout=timeout)

        output_parts = []
        if result.get("stdout"):
            output_parts.append(f"STDOUT:\n{result['stdout']}")
        if result.get("stderr"):
            output_parts.append(f"STDERR:\n{result['stderr']}")

        output_text = "\n\n".join(output_parts) if output_parts else "(no output)"

        exit_code = result.get("exit_code", -1)
        success = result.get("success", False)

        duration_ms = (time.time() - start_time) * 1000

        if success:
            logger.info(f"[TOOL] sandbox_run_command success: exit_code={exit_code}")
        else:
            logger.warning(f"[TOOL] sandbox_run_command failed: exit_code={exit_code}, stderr={result.get('stderr', '')[:200]}")

        if slogger:
            slogger.log_tool_call(
                tool_id=tool_id,
                tool_name="sandbox_run_command",
                input_data=args,
                duration_ms=duration_ms,
                success=success,
                output={"exit_code": exit_code, "stdout_len": len(result.get("stdout", "")), "stderr_len": len(result.get("stderr", ""))}
            )

        return {
            "content": [{
                "type": "text",
                "text": f"Command: {command}\nExit code: {exit_code}\n\n{output_text}"
            }],
            # Include structured data for frontend
            "stdout": result.get("stdout", ""),
            "stderr": result.get("stderr", ""),
            "exit_code": exit_code,
            "success": success
        }
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(f"[TOOL] sandbox_run_command exception: {command[:50]} - {e}", exc_info=True)

        if slogger:
            slogger.log_tool_call(
                tool_id=tool_id,
                tool_name="sandbox_run_command",
                input_data=args,
                duration_ms=duration_ms,
                success=False,
                output=str(e)
            )
            slogger.log_error("sandbox_run_command", str(e), traceback.format_exc())

        return {
            "content": [{
                "type": "text",
                "text": f"Error running command: {str(e)}"
            }],
            "isError": True
        }


@tool(
    "sandbox_list_files",
    "List files and directories in a specific path within the E2B sandbox. Use this to explore the sandbox filesystem structure.",
    {"path": str}
)
async def sandbox_list_files(args: dict[str, Any]) -> dict[str, Any]:
    """
    List files and directories in a given path.

    Args:
        path: The directory path to list (e.g., '/home/user', '.')

    Returns:
        List of files and directories, or error details
    """
    start_time = time.time()
    session_id = get_session_id()
    slogger = get_session_logger(session_id) if session_id else None
    tool_id = f"tool_{int(start_time*1000)}"

    path = args.get("path", "/home/user")
    logger.info(f"[TOOL] sandbox_list_files called: path={path}")

    try:
        manager = get_manager()
        files = await manager.list_files(path)

        duration_ms = (time.time() - start_time) * 1000
        logger.info(f"[TOOL] sandbox_list_files success: {path} ({len(files)} items)")

        if slogger:
            slogger.log_tool_call(
                tool_id=tool_id,
                tool_name="sandbox_list_files",
                input_data=args,
                duration_ms=duration_ms,
                success=True,
                output={"count": len(files)}
            )

        return {
            "content": [{
                "type": "text",
                "text": f"Directory listing for {path}:\n\n" + "\n".join(files)
            }]
        }
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(f"[TOOL] sandbox_list_files failed: {path} - {e}", exc_info=True)

        if slogger:
            slogger.log_tool_call(
                tool_id=tool_id,
                tool_name="sandbox_list_files",
                input_data=args,
                duration_ms=duration_ms,
                success=False,
                output=str(e)
            )
            slogger.log_error("sandbox_list_files", str(e), traceback.format_exc())

        return {
            "content": [{
                "type": "text",
                "text": f"Error listing files: {str(e)}"
            }],
            "isError": True
        }


@tool(
    "sandbox_get_preview_url",
    "Get the public preview URL for a web app running in the E2B sandbox. Call this after starting a dev server to get the URL where the app is accessible. The port is automatically allocated - do not specify a port.",
    {"port": int}
)
async def sandbox_get_preview_url(args: dict[str, Any]) -> dict[str, Any]:
    """
    Get the public preview URL for the sandbox.

    Args:
        port: Optional port number (will be ignored, port is auto-allocated)

    Returns:
        The public HTTPS URL for accessing the sandbox, or error details
    """
    start_time = time.time()
    session_id = get_session_id()
    slogger = get_session_logger(session_id) if session_id else None
    tool_id = f"tool_{int(start_time*1000)}"

    # Port parameter is ALWAYS ignored - we use the allocated port from sandbox manager
    # This prevents Claude from accidentally using port 3000 (frontend port)
    requested_port = args.get("port")
    logger.info(f"[TOOL] sandbox_get_preview_url called: requested_port={requested_port} (IGNORED - using allocated port)")

    try:
        manager = get_manager()
        # Always pass None to force using allocated port
        url = await manager.get_preview_url(None)

        duration_ms = (time.time() - start_time) * 1000
        logger.info(f"[TOOL] sandbox_get_preview_url success: {url}")

        if slogger:
            slogger.log_tool_call(
                tool_id=tool_id,
                tool_name="sandbox_get_preview_url",
                input_data=args,
                duration_ms=duration_ms,
                success=True,
                output={"url": url}
            )

        # Return as proper MCP format: content must be a LIST of dicts
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Preview URL: {url}\n\nThe application is accessible at {url}."
                }
            ],
            # Also include structured data for frontend extraction
            "preview_url": url,
            "url": url
        }
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(f"[TOOL] sandbox_get_preview_url failed: port={port} - {e}", exc_info=True)

        if slogger:
            slogger.log_tool_call(
                tool_id=tool_id,
                tool_name="sandbox_get_preview_url",
                input_data=args,
                duration_ms=duration_ms,
                success=False,
                output=str(e)
            )
            slogger.log_error("sandbox_get_preview_url", str(e), traceback.format_exc())

        return {
            "content": [{
                "type": "text",
                "text": f"Error getting preview URL: {str(e)}"
            }],
            "isError": True
        }


@tool(
    "sandbox_install_packages",
    "Install npm packages in the E2B sandbox. Use this to add Node.js dependencies.",
    {"packages": list}
)
async def sandbox_install_packages(args: dict[str, Any]) -> dict[str, Any]:
    """
    Install npm packages in the sandbox.

    Args:
        packages: List of npm package names to install (e.g., ['react', 'tailwindcss'])

    Returns:
        Installation output and status, or error details
    """
    start_time = time.time()
    session_id = get_session_id()
    slogger = get_session_logger(session_id) if session_id else None
    tool_id = f"tool_{int(start_time*1000)}"

    packages = args.get("packages", [])
    logger.info(f"[TOOL] sandbox_install_packages called: packages={packages}")

    try:
        if not packages or not isinstance(packages, list):
            duration_ms = (time.time() - start_time) * 1000
            logger.warning("[TOOL] sandbox_install_packages: invalid packages argument")

            if slogger:
                slogger.log_tool_call(
                    tool_id=tool_id,
                    tool_name="sandbox_install_packages",
                    input_data=args,
                    duration_ms=duration_ms,
                    success=False,
                    output="Invalid packages argument"
                )

            return {
                "content": [{
                    "type": "text",
                    "text": "Error: packages must be a non-empty list of package names"
                }],
                "isError": True
            }

        manager = get_manager()

        # Join package names and run npm install
        packages_str = " ".join(packages)
        command = f"npm install {packages_str}"

        # Use longer timeout for package installation (5 minutes)
        result = await manager.run_command(command, timeout=300)

        duration_ms = (time.time() - start_time) * 1000

        if not result.get("success", False):
            error_msg = result.get("stderr", "Installation failed")
            logger.warning(f"[TOOL] sandbox_install_packages failed: {error_msg[:200]}")

            if slogger:
                slogger.log_tool_call(
                    tool_id=tool_id,
                    tool_name="sandbox_install_packages",
                    input_data=args,
                    duration_ms=duration_ms,
                    success=False,
                    output={"error": error_msg[:500]}
                )

            return {
                "content": [{
                    "type": "text",
                    "text": f"Error installing packages: {error_msg}"
                }],
                "isError": True
            }

        output_parts = [f"Installed packages: {', '.join(packages)}"]
        if result.get("stdout"):
            output_parts.append(f"Output:\n{result['stdout']}")

        logger.info(f"[TOOL] sandbox_install_packages success: {len(packages)} packages installed")

        if slogger:
            slogger.log_tool_call(
                tool_id=tool_id,
                tool_name="sandbox_install_packages",
                input_data=args,
                duration_ms=duration_ms,
                success=True,
                output={"packages": packages, "count": len(packages)}
            )

        return {
            "content": [{
                "type": "text",
                "text": "\n\n".join(output_parts)
            }]
        }
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(f"[TOOL] sandbox_install_packages exception: {e}", exc_info=True)

        if slogger:
            slogger.log_tool_call(
                tool_id=tool_id,
                tool_name="sandbox_install_packages",
                input_data=args,
                duration_ms=duration_ms,
                success=False,
                output=str(e)
            )
            slogger.log_error("sandbox_install_packages", str(e), traceback.format_exc())

        return {
            "content": [{
                "type": "text",
                "text": f"Error installing packages: {str(e)}"
            }],
            "isError": True
        }


@tool(
    "sandbox_start_dev_server",
    "Start the Next.js development server in the background and get the preview URL. Use this AFTER running npm install to start the app and get the live preview URL. The port is automatically allocated (NOT 3000) - do not specify a port parameter. Returns the preview URL in the response.",
    {"project_dir": str}
)
async def sandbox_start_dev_server(args: dict[str, Any]) -> dict[str, Any]:
    """
    Start development server and return preview URL.

    Args:
        project_dir: Directory containing the Next.js project (default: current directory)

    Returns:
        Preview URL where the app is accessible (port is auto-allocated, never 3000)
    """
    start_time = time.time()
    session_id = get_session_id()
    slogger = get_session_logger(session_id) if session_id else None
    tool_id = f"tool_{int(start_time*1000)}"

    project_dir = args.get("project_dir", ".")
    # Port is auto-allocated by the sandbox manager - ignore any port parameter
    port = args.get("port")  # Will be ignored by manager
    logger.info(f"[TOOL] sandbox_start_dev_server called: project_dir={project_dir}, port={port}")

    # Debug: Check if sandbox manager is available
    try:
        manager = get_manager()
        logger.info(f"[TOOL] sandbox_start_dev_server: manager available, is_initialized={manager.is_initialized}, allocated_port={manager._allocated_port}")
    except Exception as e:
        logger.error(f"[TOOL] sandbox_start_dev_server: failed to get manager: {e}")
        return {
            "content": [{
                "type": "text",
                "text": f"Error: Sandbox manager not available: {str(e)}"
            }],
            "isError": True
        }

    try:
        manager = get_manager()
        result = await manager.start_dev_server(project_dir, port)

        duration_ms = (time.time() - start_time) * 1000

        if result.get("success"):
            logger.info(f"[TOOL] sandbox_start_dev_server success: {result['preview_url']}")

            if slogger:
                slogger.log_tool_call(
                    tool_id=tool_id,
                    tool_name="sandbox_start_dev_server",
                    input_data=args,
                    duration_ms=duration_ms,
                    success=True,
                    output={"preview_url": result["preview_url"]}
                )

            # Return as proper MCP format: content must be a LIST of dicts
            # Include preview_url in text so Claude sees it
            preview_url = result["preview_url"]
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"SUCCESS: Dev server started!\n\nPreview URL: {preview_url}\n\nThe application is now running and accessible at {preview_url}. Do NOT try to start the server again - it is already running!"
                    }
                ],
                # Also include structured data for frontend extraction
                "preview_url": preview_url,
                "url": preview_url
            }
        else:
            error_msg = result.get('error', 'Unknown error')
            logger.warning(f"[TOOL] sandbox_start_dev_server failed: {error_msg}")

            if slogger:
                slogger.log_tool_call(
                    tool_id=tool_id,
                    tool_name="sandbox_start_dev_server",
                    input_data=args,
                    duration_ms=duration_ms,
                    success=False,
                    output={"error": error_msg}
                )

            return {
                "content": [{
                    "type": "text",
                    "text": f"Failed to start dev server: {error_msg}"
                }],
                "isError": True
            }
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(f"[TOOL] sandbox_start_dev_server exception: {e}", exc_info=True)

        if slogger:
            slogger.log_tool_call(
                tool_id=tool_id,
                tool_name="sandbox_start_dev_server",
                input_data=args,
                duration_ms=duration_ms,
                success=False,
                output=str(e)
            )
            slogger.log_error("sandbox_start_dev_server", str(e), traceback.format_exc())

        return {
            "content": [{
                "type": "text",
                "text": f"Error starting dev server: {str(e)}"
            }],
            "isError": True
        }


def create_sandbox_tools_server(sandbox_manager, session_id: str = None):
    """
    Create an MCP server with ALL E2B sandbox tools (legacy, for E2B cloud mode).

    Args:
        sandbox_manager: The sandbox manager instance that provides access to active sandboxes
        session_id: Optional session ID for logging (if not provided, logging will be limited)

    Returns:
        An MCP server instance configured with all sandbox tools
    """
    set_sandbox_manager(sandbox_manager)
    if session_id:
        set_session_id(session_id)

    return create_sdk_mcp_server(
        name="sandbox",
        version="1.0.0",
        tools=[
            sandbox_write_file,
            sandbox_read_file,
            sandbox_run_command,
            sandbox_list_files,
            sandbox_get_preview_url,
            sandbox_install_packages,
            sandbox_start_dev_server,
        ]
    )


def create_e2b_only_server(sandbox_manager, session_id: str = None):
    """
    Create a minimal MCP server with only E2B-specific tools (for LOCAL mode with native tools).

    This server only provides tools that native Claude Code tools cannot handle:
    - get_preview_url: Returns the correct localhost URL
    - start_dev_server: Starts the Next.js dev server in background

    File operations (Read, Write, Edit, Bash, Glob, Grep) are handled by native tools.

    Args:
        sandbox_manager: The sandbox manager instance
        session_id: Optional session ID for logging

    Returns:
        An MCP server instance with only E2B-specific tools
    """
    set_sandbox_manager(sandbox_manager)
    if session_id:
        set_session_id(session_id)

    return create_sdk_mcp_server(
        name="e2b",
        version="1.0.0",
        tools=[
            sandbox_get_preview_url,
            sandbox_start_dev_server,
        ]
    )
