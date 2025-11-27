"""
E2B Sandbox MCP Tools for Claude Agent SDK

Provides tools for interacting with E2B sandboxes through the Claude Agent SDK MCP server.
These tools allow Claude to manage files, run commands, and interact with sandboxes.
"""

from typing import Any

from claude_agent_sdk import tool, create_sdk_mcp_server

# Global reference to the sandbox manager
_sandbox_manager = None


def set_sandbox_manager(manager):
    """Set the global sandbox manager instance."""
    global _sandbox_manager
    _sandbox_manager = manager


async def get_sandbox():
    """Get or create sandbox from the manager (lazy initialization)."""
    if _sandbox_manager is None:
        raise RuntimeError("Sandbox manager not initialized. Call set_sandbox_manager first.")

    # Use ensure_sandbox for lazy initialization
    sandbox = await _sandbox_manager.ensure_sandbox()
    return sandbox


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
    try:
        file_path = args["file_path"]
        content = args["content"]

        sandbox = await get_sandbox()
        await sandbox.files.write(file_path, content)

        return {
            "content": [{
                "type": "text",
                "text": f"Successfully wrote {len(content)} characters to {file_path}"
            }]
        }
    except Exception as e:
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
    try:
        file_path = args["file_path"]

        sandbox = await get_sandbox()
        content = await sandbox.files.read(file_path)

        return {
            "content": [{
                "type": "text",
                "text": f"File: {file_path}\n\n{content}"
            }]
        }
    except Exception as e:
        return {
            "content": [{
                "type": "text",
                "text": f"Error reading file: {str(e)}"
            }],
            "isError": True
        }


@tool(
    "sandbox_run_command",
    "Execute a shell command in the E2B sandbox. Use this to run bash commands, scripts, or system utilities. Returns both stdout and stderr.",
    {"command": str}
)
async def sandbox_run_command(args: dict[str, Any]) -> dict[str, Any]:
    """
    Execute a shell command in the sandbox.

    Args:
        command: The shell command to execute (e.g., 'ls -la', 'python script.py')

    Returns:
        The command output (stdout and stderr), exit code, and any errors
    """
    try:
        command = args["command"]

        sandbox = await get_sandbox()
        result = await sandbox.commands.run(command)

        output_parts = []
        if result.stdout:
            output_parts.append(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            output_parts.append(f"STDERR:\n{result.stderr}")

        output_text = "\n\n".join(output_parts) if output_parts else "(no output)"

        return {
            "content": [{
                "type": "text",
                "text": f"Command: {command}\nExit code: {result.exit_code}\n\n{output_text}"
            }]
        }
    except Exception as e:
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
    try:
        path = args["path"]

        sandbox = await get_sandbox()
        result = await sandbox.commands.run(f"ls -lah {path}")

        if result.exit_code != 0:
            return {
                "content": [{
                    "type": "text",
                    "text": f"Error listing directory: {result.stderr or 'Unknown error'}"
                }],
                "isError": True
            }

        return {
            "content": [{
                "type": "text",
                "text": f"Directory listing for {path}:\n\n{result.stdout}"
            }]
        }
    except Exception as e:
        return {
            "content": [{
                "type": "text",
                "text": f"Error listing files: {str(e)}"
            }],
            "isError": True
        }


@tool(
    "sandbox_get_preview_url",
    "Get the public preview URL for the E2B sandbox. Use this to retrieve the HTTPS URL where web applications running in the sandbox can be accessed.",
    {}
)
async def sandbox_get_preview_url(args: dict[str, Any]) -> dict[str, Any]:
    """
    Get the public preview URL for the sandbox.

    Args:
        (none)

    Returns:
        The public HTTPS URL for accessing the sandbox, or error details
    """
    try:
        sandbox = await get_sandbox()

        # Get the public URL for port 3000 (Next.js default)
        port = 3000
        host = sandbox.get_host(port)
        public_url = f"https://{host}"

        return {
            "content": [{
                "type": "text",
                "text": f"Preview URL: {public_url}"
            }]
        }
    except Exception as e:
        return {
            "content": [{
                "type": "text",
                "text": f"Error getting preview URL: {str(e)}"
            }],
            "isError": True
        }


@tool(
    "sandbox_install_packages",
    "Install npm packages in the E2B sandbox. Use this to install Node.js dependencies needed for JavaScript/TypeScript applications.",
    {"packages": list}
)
async def sandbox_install_packages(args: dict[str, Any]) -> dict[str, Any]:
    """
    Install npm packages in the sandbox.

    Args:
        packages: List of npm package names to install (e.g., ['react', 'express', 'axios'])

    Returns:
        Installation output and status, or error details
    """
    try:
        packages = args["packages"]

        if not packages or not isinstance(packages, list):
            return {
                "content": [{
                    "type": "text",
                    "text": "Error: packages must be a non-empty list of package names"
                }],
                "isError": True
            }

        sandbox = await get_sandbox()

        # Join package names and run npm install
        packages_str = " ".join(packages)
        command = f"npm install {packages_str}"

        result = await sandbox.commands.run(command)

        output_parts = [f"Installed packages: {', '.join(packages)}"]

        if result.stdout:
            output_parts.append(f"Output:\n{result.stdout}")

        if result.exit_code != 0:
            error_msg = result.stderr or "Installation failed"
            return {
                "content": [{
                    "type": "text",
                    "text": f"Error installing packages: {error_msg}"
                }],
                "isError": True
            }

        return {
            "content": [{
                "type": "text",
                "text": "\n\n".join(output_parts)
            }]
        }
    except Exception as e:
        return {
            "content": [{
                "type": "text",
                "text": f"Error installing packages: {str(e)}"
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
        ]
    )
