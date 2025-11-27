"""
E2B Sandbox MCP Tools for Claude Agent SDK

Provides tools for interacting with E2B sandboxes through the Claude Agent SDK MCP server.
These tools allow Claude to manage files, run commands, and interact with sandboxes.
"""

import logging
from typing import Any

from claude_agent_sdk import tool, create_sdk_mcp_server

# Configure logging
logger = logging.getLogger(__name__)

# Global reference to the sandbox manager
_sandbox_manager = None


def set_sandbox_manager(manager):
    """Set the global sandbox manager instance."""
    global _sandbox_manager
    _sandbox_manager = manager
    logger.info("Sandbox manager set for MCP tools")


def get_manager():
    """Get the sandbox manager, ensuring it's initialized."""
    if _sandbox_manager is None:
        logger.error("Sandbox manager not initialized when tool was called")
        raise RuntimeError("Sandbox manager not initialized. Call set_sandbox_manager first.")
    return _sandbox_manager


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
    file_path = args.get("file_path", "unknown")
    content_len = len(args.get("content", ""))
    logger.info(f"[TOOL] sandbox_write_file called: path={file_path}, content_size={content_len} bytes")

    try:
        content = args["content"]

        manager = get_manager()
        result = await manager.write_file(file_path, content)

        logger.info(f"[TOOL] sandbox_write_file success: {file_path} ({result['size']} bytes)")
        return {
            "content": [{
                "type": "text",
                "text": f"Successfully wrote {result['size']} bytes to {file_path}"
            }]
        }
    except Exception as e:
        logger.error(f"[TOOL] sandbox_write_file failed: {file_path} - {e}", exc_info=True)
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
    file_path = args.get("file_path", "unknown")
    logger.info(f"[TOOL] sandbox_read_file called: path={file_path}")

    try:
        manager = get_manager()
        content = await manager.read_file(file_path)

        logger.info(f"[TOOL] sandbox_read_file success: {file_path} ({len(content)} bytes)")
        return {
            "content": [{
                "type": "text",
                "text": f"File: {file_path}\n\n{content}"
            }]
        }
    except Exception as e:
        logger.error(f"[TOOL] sandbox_read_file failed: {file_path} - {e}", exc_info=True)
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

        if success:
            logger.info(f"[TOOL] sandbox_run_command success: exit_code={exit_code}")
        else:
            logger.warning(f"[TOOL] sandbox_run_command failed: exit_code={exit_code}, stderr={result.get('stderr', '')[:200]}")

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
        logger.error(f"[TOOL] sandbox_run_command exception: {command[:50]} - {e}", exc_info=True)
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
    path = args.get("path", "/home/user")
    logger.info(f"[TOOL] sandbox_list_files called: path={path}")

    try:
        manager = get_manager()
        files = await manager.list_files(path)

        logger.info(f"[TOOL] sandbox_list_files success: {path} ({len(files)} items)")
        return {
            "content": [{
                "type": "text",
                "text": f"Directory listing for {path}:\n\n" + "\n".join(files)
            }]
        }
    except Exception as e:
        logger.error(f"[TOOL] sandbox_list_files failed: {path} - {e}", exc_info=True)
        return {
            "content": [{
                "type": "text",
                "text": f"Error listing files: {str(e)}"
            }],
            "isError": True
        }


@tool(
    "sandbox_get_preview_url",
    "Get the public preview URL for a web app running in the E2B sandbox. Call this after starting a dev server (e.g., 'npm run dev &') to get the URL where the app is accessible.",
    {"port": int}
)
async def sandbox_get_preview_url(args: dict[str, Any]) -> dict[str, Any]:
    """
    Get the public preview URL for the sandbox.

    Args:
        port: The port number where the app is running (default: 3000 for Next.js)

    Returns:
        The public HTTPS URL for accessing the sandbox, or error details
    """
    port = args.get("port", 3000)
    logger.info(f"[TOOL] sandbox_get_preview_url called: port={port}")

    try:
        manager = get_manager()
        url = await manager.get_preview_url(port)

        logger.info(f"[TOOL] sandbox_get_preview_url success: {url}")
        # Return preview_url in content dict so it gets passed through SDK
        return {
            "content": {
                "type": "preview_url_result",
                "text": f"Preview URL: {url}\n\nThe application is now accessible at this URL.",
                "preview_url": url,
                "url": url
            }
        }
    except Exception as e:
        logger.error(f"[TOOL] sandbox_get_preview_url failed: port={port} - {e}", exc_info=True)
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
    packages = args.get("packages", [])
    logger.info(f"[TOOL] sandbox_install_packages called: packages={packages}")

    try:
        if not packages or not isinstance(packages, list):
            logger.warning("[TOOL] sandbox_install_packages: invalid packages argument")
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

        if not result.get("success", False):
            error_msg = result.get("stderr", "Installation failed")
            logger.warning(f"[TOOL] sandbox_install_packages failed: {error_msg[:200]}")
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
        return {
            "content": [{
                "type": "text",
                "text": "\n\n".join(output_parts)
            }]
        }
    except Exception as e:
        logger.error(f"[TOOL] sandbox_install_packages exception: {e}", exc_info=True)
        return {
            "content": [{
                "type": "text",
                "text": f"Error installing packages: {str(e)}"
            }],
            "isError": True
        }


@tool(
    "sandbox_start_dev_server",
    "Start the Next.js development server in the background and get the preview URL. Use this AFTER running npm install to start the app and get the live preview URL.",
    {"project_dir": str, "port": int}
)
async def sandbox_start_dev_server(args: dict[str, Any]) -> dict[str, Any]:
    """
    Start development server and return preview URL.

    Args:
        project_dir: Directory containing the Next.js project
        port: Port to run on (default: 3000)

    Returns:
        Preview URL where the app is accessible
    """
    project_dir = args.get("project_dir", ".")
    port = args.get("port", 3000)
    logger.info(f"[TOOL] sandbox_start_dev_server called: project_dir={project_dir}, port={port}")

    try:
        manager = get_manager()
        result = await manager.start_dev_server(project_dir, port)

        if result.get("success"):
            logger.info(f"[TOOL] sandbox_start_dev_server success: {result['preview_url']}")
            # Return preview_url in content dict so it gets passed through SDK
            return {
                "content": {
                    "type": "dev_server_result",
                    "text": f"Dev server started successfully!\n\nPreview URL: {result['preview_url']}\n\nThe application is now running and accessible at this URL.",
                    "preview_url": result["preview_url"],
                    "url": result["preview_url"]
                }
            }
        else:
            error_msg = result.get('error', 'Unknown error')
            logger.warning(f"[TOOL] sandbox_start_dev_server failed: {error_msg}")
            return {
                "content": [{
                    "type": "text",
                    "text": f"Failed to start dev server: {error_msg}"
                }],
                "isError": True
            }
    except Exception as e:
        logger.error(f"[TOOL] sandbox_start_dev_server exception: {e}", exc_info=True)
        return {
            "content": [{
                "type": "text",
                "text": f"Error starting dev server: {str(e)}"
            }],
            "isError": True
        }


def create_sandbox_tools_server(sandbox_manager):
    """
    Create an MCP server with E2B sandbox tools.

    Args:
        sandbox_manager: The sandbox manager instance that provides access to active sandboxes

    Returns:
        An MCP server instance configured with all sandbox tools
    """
    set_sandbox_manager(sandbox_manager)

    return create_sdk_mcp_server(
        name="e2b-sandbox",
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
