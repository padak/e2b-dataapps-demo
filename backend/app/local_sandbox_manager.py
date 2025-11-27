"""
Local Sandbox Manager for local filesystem-based code execution.

This module provides a LocalSandboxManager class that mimics the E2B SandboxManager
API but runs everything on the local filesystem for development and testing.
"""

import asyncio
import logging
import socket
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LocalSandboxError(Exception):
    """Base exception for local sandbox-related errors."""
    pass


class LocalSandboxInitializationError(LocalSandboxError):
    """Raised when local sandbox initialization fails."""
    pass


class LocalSandboxFileOperationError(LocalSandboxError):
    """Raised when file operations fail."""
    pass


class LocalSandboxCommandError(LocalSandboxError):
    """Raised when command execution fails."""
    pass


class LocalSandboxManager:
    """
    Manages local filesystem-based sandbox lifecycle with API matching SandboxManager.

    Uses local filesystem operations and subprocess for command execution.
    """

    def __init__(
        self,
        template: str = "local",
        timeout_seconds: int = 1800,
        session_id: Optional[str] = None
    ):
        """
        Initialize the LocalSandboxManager.

        Args:
            template: Template name (unused for local, but kept for API compatibility)
            timeout_seconds: Timeout in seconds (unused for local, but kept for API compatibility)
            session_id: Unique session identifier for logging context
        """
        self._template: str = template
        self._timeout: int = timeout_seconds
        self._session_id: str = session_id or "unknown"
        self._is_initialized: bool = False
        self._project_dir: Optional[Path] = None
        self._allocated_port: Optional[int] = None
        self._dev_server_process: Optional[subprocess.Popen] = None

        logger.info(
            f"[{self._session_id}] LocalSandboxManager initialized with template='{template}', "
            f"timeout={timeout_seconds}s"
        )

    def _find_available_port(self, start_port: int = 3001) -> int:
        """Find an available port starting from start_port."""
        port = start_port
        while port < start_port + 100:  # Try up to 100 ports
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('', port))
                    logger.debug(f"[{self._session_id}] Port {port} is available")
                    return port
            except OSError:
                logger.debug(f"[{self._session_id}] Port {port} is in use, trying next")
                port += 1
        raise LocalSandboxInitializationError(f"No available ports found in range {start_port}-{start_port + 100}")

    def _resolve_path(self, project_dir: Path, path: str) -> Path:
        """
        Resolve a path relative to project directory.

        Handles:
        - Relative paths: treated as relative to project_dir
        - Absolute paths inside sandbox: used directly
        - Absolute paths outside sandbox: treated as relative
        - macOS /tmp vs /private/tmp symlink differences
        """
        path_obj = Path(path)

        if not path_obj.is_absolute():
            return project_dir / path

        # Resolve symlinks for comparison (e.g., /tmp -> /private/tmp on macOS)
        try:
            resolved_path = path_obj.resolve()
            resolved_project = project_dir.resolve()

            # Check if path is inside our sandbox (after resolving symlinks)
            try:
                relative = resolved_path.relative_to(resolved_project)
                # Path is inside sandbox - use it directly
                return resolved_project / relative
            except ValueError:
                pass

            # Also check with /private prefix handling for macOS
            path_str = str(resolved_path)
            project_str = str(resolved_project)

            # Handle /private/tmp vs /tmp
            if path_str.startswith('/private/tmp/') and project_str.startswith('/tmp/'):
                # Try matching with /private prefix
                private_project = Path('/private') / project_dir.relative_to('/')
                try:
                    relative = resolved_path.relative_to(private_project.resolve())
                    return resolved_project / relative
                except ValueError:
                    pass

        except (OSError, RuntimeError):
            # Path resolution failed, fall back to simple handling
            pass

        # Path is absolute but outside sandbox - treat as relative
        return project_dir / path.lstrip('/')

    async def ensure_sandbox(self, template: Optional[str] = None) -> Path:
        """Ensure project directory is created and return it (lazy initialization)."""
        if self._is_initialized and self._project_dir is not None:
            logger.debug(f"[{self._session_id}] Sandbox already initialized, returning existing directory")
            return self._project_dir

        try:
            # Create project directory
            base_dir = Path("/tmp/app-builder")
            base_dir.mkdir(parents=True, exist_ok=True)

            self._project_dir = base_dir / self._session_id
            self._project_dir.mkdir(parents=True, exist_ok=True)

            # Allocate a port
            self._allocated_port = self._find_available_port(start_port=3001)

            self._is_initialized = True
            logger.info(
                f"[{self._session_id}] Local sandbox created successfully at: {self._project_dir} "
                f"(allocated port: {self._allocated_port})"
            )

            return self._project_dir

        except Exception as e:
            error_msg = f"[{self._session_id}] Failed to create local sandbox directory: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise LocalSandboxInitializationError(error_msg) from e

    async def write_file(self, path: str, content: str) -> Dict[str, Any]:
        """Write content to a file in the local filesystem."""
        try:
            project_dir = await self.ensure_sandbox()

            # Resolve path - handle both absolute and relative paths
            # Note: On macOS, /tmp is symlink to /private/tmp, so resolve both
            file_path = self._resolve_path(project_dir, path)

            logger.debug(f"[{self._session_id}] Writing file to path: {file_path}")

            # Create parent directories if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            await asyncio.to_thread(file_path.write_text, content, encoding='utf-8')

            result = {
                "success": True,
                "path": str(file_path),
                "size": len(content.encode('utf-8'))
            }

            logger.info(f"[{self._session_id}] Successfully wrote {result['size']} bytes to {file_path}")
            return result

        except LocalSandboxInitializationError:
            raise
        except Exception as e:
            error_msg = f"[{self._session_id}] Failed to write file to '{path}': {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise LocalSandboxFileOperationError(error_msg) from e

    async def read_file(self, path: str) -> str:
        """Read content from a file in the local filesystem."""
        try:
            project_dir = await self.ensure_sandbox()

            # Resolve path - handle both absolute and relative paths
            file_path = self._resolve_path(project_dir, path)

            logger.debug(f"[{self._session_id}] Reading file from path: {file_path}")

            # Read file
            content = await asyncio.to_thread(file_path.read_text, encoding='utf-8')

            logger.info(f"[{self._session_id}] Successfully read {len(content)} bytes from {file_path}")
            return content

        except LocalSandboxInitializationError:
            raise
        except FileNotFoundError as e:
            error_msg = f"[{self._session_id}] File not found: '{path}'"
            logger.error(error_msg)
            raise LocalSandboxFileOperationError(error_msg) from e
        except Exception as e:
            error_msg = f"[{self._session_id}] Failed to read file from '{path}': {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise LocalSandboxFileOperationError(error_msg) from e

    async def run_command(self, command: str, timeout: Optional[int] = 120, background: bool = False) -> Dict[str, Any]:
        """Execute a shell command using subprocess.

        Args:
            command: Shell command to execute
            timeout: Command timeout in seconds (default 120, use 0 or None for no timeout)
            background: If True, start process in background and return immediately
        """
        try:
            project_dir = await self.ensure_sandbox()
            logger.info(
                f"[{self._session_id}] Executing command: {command[:80]}{'...' if len(command) > 80 else ''} "
                f"(timeout={timeout}s, background={background})"
            )

            if background:
                # Start process in background
                process = await asyncio.to_thread(
                    subprocess.Popen,
                    command,
                    shell=True,
                    cwd=str(project_dir),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )

                # Give process time to start
                await asyncio.sleep(2)

                logger.info(f"[{self._session_id}] Background process started with PID: {process.pid}")
                return {
                    "stdout": "Process started in background",
                    "stderr": "",
                    "exit_code": 0,
                    "success": True,
                    "background": True,
                    "pid": process.pid
                }
            else:
                # Regular command with timeout
                timeout_value = timeout if timeout and timeout > 0 else None

                process = await asyncio.create_subprocess_shell(
                    command,
                    cwd=str(project_dir),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )

                try:
                    stdout_bytes, stderr_bytes = await asyncio.wait_for(
                        process.communicate(),
                        timeout=timeout_value
                    )
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()
                    raise LocalSandboxCommandError(
                        f"Command timed out after {timeout} seconds: {command[:50]}"
                    )

                stdout = stdout_bytes.decode('utf-8') if stdout_bytes else ""
                stderr = stderr_bytes.decode('utf-8') if stderr_bytes else ""
                exit_code = process.returncode or 0

                result = {
                    "stdout": stdout,
                    "stderr": stderr,
                    "exit_code": exit_code,
                    "success": exit_code == 0
                }

                if result['success']:
                    logger.info(
                        f"[{self._session_id}] Command executed successfully: {command[:50]}... "
                        f"(exit_code={result['exit_code']})"
                    )
                else:
                    logger.warning(
                        f"[{self._session_id}] Command failed: {command[:50]}... "
                        f"(exit_code={result['exit_code']}, stderr={result['stderr'][:100] if result['stderr'] else ''})"
                    )

                return result

        except LocalSandboxInitializationError:
            raise
        except LocalSandboxCommandError:
            raise
        except Exception as e:
            error_msg = f"[{self._session_id}] Failed to execute command '{command[:50]}': {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise LocalSandboxCommandError(error_msg) from e

    async def start_dev_server(self, project_dir: str = ".", port: Optional[int] = None) -> Dict[str, Any]:
        """Start a development server in the background and return preview URL.

        Args:
            project_dir: Directory containing the project (default: current dir, relative to sandbox root)
            port: Port to run the server on (default: use allocated port)

        Returns:
            Dict with preview_url and status
        """
        try:
            sandbox_root = await self.ensure_sandbox()

            # Use allocated port if not specified
            server_port = port or self._allocated_port
            if not server_port:
                server_port = self._find_available_port(start_port=3001)
                self._allocated_port = server_port

            # Resolve project directory - handle absolute and relative paths
            if project_dir == ".":
                work_dir = sandbox_root
            else:
                work_dir = self._resolve_path(sandbox_root, project_dir)

            # Start dev server in background
            command = f"PORT={server_port} npm run dev"
            logger.info(f"[{self._session_id}] Starting dev server in {work_dir}: {command}")

            self._dev_server_process = await asyncio.to_thread(
                subprocess.Popen,
                command,
                shell=True,
                cwd=str(work_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Wait for server to start
            logger.info(f"[{self._session_id}] Waiting for dev server to start...")
            await asyncio.sleep(5)

            # Check if server is running
            if self._dev_server_process.poll() is not None:
                # Process died
                stdout, stderr = self._dev_server_process.communicate()
                error_msg = f"Dev server failed to start. stderr: {stderr}"
                logger.error(f"[{self._session_id}] {error_msg}")
                return {
                    "success": False,
                    "error": error_msg
                }

            # Get preview URL
            preview_url = f"http://localhost:{server_port}"

            logger.info(f"[{self._session_id}] Dev server started, preview URL: {preview_url}")

            return {
                "success": True,
                "preview_url": preview_url,
                "port": server_port,
                "message": f"Dev server started on port {server_port}",
                "pid": self._dev_server_process.pid
            }

        except Exception as e:
            error_msg = f"[{self._session_id}] Failed to start dev server: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "error": error_msg
            }

    async def list_files(self, path: str = ".") -> List[str]:
        """List files in a directory in the local filesystem."""
        try:
            project_dir = await self.ensure_sandbox()

            # Resolve path - handle both absolute and relative paths
            if path == "." or path == "/":
                list_path = project_dir
            else:
                list_path = self._resolve_path(project_dir, path)

            logger.debug(f"[{self._session_id}] Listing files in path: {list_path}")

            if not list_path.exists():
                raise LocalSandboxFileOperationError(f"Directory not found: '{path}'")

            if not list_path.is_dir():
                raise LocalSandboxFileOperationError(f"Not a directory: '{path}'")

            # List files
            files = [item.name for item in list_path.iterdir()]

            logger.info(f"[{self._session_id}] Found {len(files)} items in {list_path}")
            return files

        except LocalSandboxInitializationError:
            raise
        except LocalSandboxFileOperationError:
            raise
        except Exception as e:
            error_msg = f"[{self._session_id}] Failed to list files in '{path}': {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise LocalSandboxFileOperationError(error_msg) from e

    async def get_preview_url(self, port: Optional[int] = None) -> str:
        """Get the preview URL for a service running on the specified port."""
        try:
            await self.ensure_sandbox()

            # Use provided port or allocated port
            server_port = port or self._allocated_port
            if not server_port:
                raise LocalSandboxError("No port allocated. Call start_dev_server first or provide a port.")

            url = f"http://localhost:{server_port}"

            logger.info(f"[{self._session_id}] Generated preview URL for port {server_port}: {url}")
            return url

        except LocalSandboxInitializationError:
            raise
        except Exception as e:
            error_msg = f"[{self._session_id}] Failed to get preview URL for port {port}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise LocalSandboxError(error_msg) from e

    async def destroy(self, delete_files: bool = False) -> None:
        """Cleanup resources and optionally delete project directory.

        Args:
            delete_files: If True, delete the project directory (default: False for safety)
        """
        if not self._is_initialized:
            logger.debug(f"[{self._session_id}] Sandbox not initialized, nothing to destroy")
            return

        try:
            logger.info(f"[{self._session_id}] Destroying local sandbox")

            # Kill dev server process if running
            if self._dev_server_process is not None:
                try:
                    logger.info(f"[{self._session_id}] Terminating dev server process (PID: {self._dev_server_process.pid})")
                    self._dev_server_process.terminate()

                    # Wait for graceful shutdown
                    try:
                        await asyncio.wait_for(
                            asyncio.to_thread(self._dev_server_process.wait),
                            timeout=5.0
                        )
                    except asyncio.TimeoutError:
                        logger.warning(f"[{self._session_id}] Process didn't terminate gracefully, killing it")
                        self._dev_server_process.kill()
                        await asyncio.to_thread(self._dev_server_process.wait)

                    logger.info(f"[{self._session_id}] Dev server process terminated")
                except Exception as e:
                    logger.warning(f"[{self._session_id}] Error terminating dev server: {e}")
                finally:
                    self._dev_server_process = None

            # Optionally delete project directory
            if delete_files and self._project_dir and self._project_dir.exists():
                logger.info(f"[{self._session_id}] Deleting project directory: {self._project_dir}")
                await asyncio.to_thread(shutil.rmtree, self._project_dir, ignore_errors=True)
                logger.info(f"[{self._session_id}] Project directory deleted")
            elif self._project_dir:
                logger.info(f"[{self._session_id}] Keeping project directory: {self._project_dir}")

            self._is_initialized = False
            self._project_dir = None
            self._allocated_port = None

            logger.info(f"[{self._session_id}] Local sandbox destroyed successfully")

        except Exception as e:
            error_msg = f"[{self._session_id}] Failed to destroy local sandbox: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise LocalSandboxError(error_msg) from e

    async def keep_alive(self, timeout_seconds: int = 1800) -> bool:
        """No-op for local sandbox (no timeout management needed).

        Args:
            timeout_seconds: Ignored for local sandbox

        Returns:
            True if sandbox is initialized, False otherwise
        """
        if not self._is_initialized:
            return False

        logger.debug(f"[{self._session_id}] keep_alive called (no-op for local sandbox)")
        return True

    @property
    def is_initialized(self) -> bool:
        """Check if the sandbox is currently initialized."""
        return self._is_initialized and self._project_dir is not None

    @property
    def sandbox_id(self) -> Optional[str]:
        """Get the current sandbox ID (session_id for local)."""
        return self._session_id if self._is_initialized else None

    @property
    def preview_url(self) -> Optional[str]:
        """Get the current preview URL if port is allocated."""
        if self._allocated_port:
            return f"http://localhost:{self._allocated_port}"
        return None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.ensure_sandbox()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - ensures cleanup."""
        await self.destroy()
        return False
