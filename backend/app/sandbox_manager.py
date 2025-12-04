"""
E2B Sandbox Manager for lifecycle management of isolated code execution environments.

This module provides a SandboxManager class that handles the creation, management,
and cleanup of E2B sandboxes with lazy initialization and comprehensive error handling.
"""

import asyncio
import logging
import os
from typing import Optional, Dict, Any, List

from e2b_code_interpreter import Sandbox


def get_keboola_envs() -> Dict[str, str]:
    """Get Keboola environment variables to pass to sandbox."""
    envs = {}

    kbc_token = os.getenv("KBC_TOKEN", "")
    if kbc_token and kbc_token != "xxx":
        envs["KBC_TOKEN"] = kbc_token
        envs["KBC_URL"] = os.getenv("KBC_URL", "https://connection.keboola.com/")
        envs["WORKSPACE_ID"] = os.getenv("WORKSPACE_ID", "")
        envs["BRANCH_ID"] = os.getenv("BRANCH_ID", "")

    return envs


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SandboxError(Exception):
    """Base exception for sandbox-related errors."""
    pass


class SandboxInitializationError(SandboxError):
    """Raised when sandbox initialization fails."""
    pass


class SandboxFileOperationError(SandboxError):
    """Raised when file operations fail."""
    pass


class SandboxCommandError(SandboxError):
    """Raised when command execution fails."""
    pass


class SandboxManager:
    """
    Manages E2B sandbox lifecycle with lazy initialization.

    Note: E2B SDK is synchronous, so we use asyncio.to_thread() to run
    blocking operations without blocking the event loop.
    """

    def __init__(
        self,
        template: str = "keboola-apps-builder",
        timeout_seconds: int = 1800,
        session_id: Optional[str] = None
    ):
        """
        Initialize the SandboxManager.

        Args:
            template: E2B template name to use for sandbox creation
            timeout_seconds: Sandbox timeout in seconds (default: 1800 = 30 minutes)
            session_id: Unique session identifier for logging context
        """
        self._sandbox: Optional[Sandbox] = None
        self._template: str = template
        self._timeout: int = timeout_seconds
        self._is_initialized: bool = False
        self._session_id: str = session_id or "unknown"

        logger.info(
            f"[{self._session_id}] SandboxManager initialized with template='{template}', "
            f"timeout={timeout_seconds}s"
        )

    def _create_sandbox_sync(self, template: str) -> Sandbox:
        """Synchronous sandbox creation."""
        # Get Keboola env vars to pass to sandbox
        envs = get_keboola_envs()
        env_keys = list(envs.keys()) if envs else []

        logger.info(f"[{self._session_id}] Calling Sandbox.create(template='{template}', timeout={self._timeout}, envs={env_keys})")
        sandbox = Sandbox.create(template=template, timeout=self._timeout, envs=envs if envs else None)
        logger.info(f"[{self._session_id}] Sandbox created: {sandbox.sandbox_id}")
        return sandbox

    async def ensure_sandbox(self, template: Optional[str] = None) -> Sandbox:
        """Ensure sandbox is created and return it (lazy initialization)."""
        if self._is_initialized and self._sandbox is not None:
            logger.debug(f"[{self._session_id}] Sandbox already initialized, returning existing instance")
            return self._sandbox

        template_to_use = template or self._template

        try:
            logger.info(
                f"[{self._session_id}] Creating sandbox with template='{template_to_use}', "
                f"timeout={self._timeout}s"
            )

            # Run synchronous E2B creation in thread pool
            self._sandbox = await asyncio.to_thread(
                self._create_sandbox_sync, template_to_use
            )

            self._is_initialized = True
            logger.info(f"[{self._session_id}] Sandbox created successfully with ID: {self._sandbox.sandbox_id}")

            return self._sandbox

        except Exception as e:
            error_msg = f"[{self._session_id}] Failed to create sandbox with template '{template_to_use}': {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise SandboxInitializationError(error_msg) from e

    async def write_file(self, path: str, content: str) -> Dict[str, Any]:
        """Write content to a file in the sandbox."""
        try:
            sandbox = await self.ensure_sandbox()
            logger.debug(f"[{self._session_id}] Writing file to path: {path}")

            # Keep sandbox alive on activity
            await self.keep_alive()

            # Run synchronous file write in thread pool
            await asyncio.to_thread(sandbox.files.write, path, content)

            result = {
                "success": True,
                "path": path,
                "size": len(content.encode('utf-8'))
            }

            logger.info(f"[{self._session_id}] Successfully wrote {result['size']} bytes to {path}")
            return result

        except SandboxInitializationError:
            raise
        except Exception as e:
            error_msg = f"[{self._session_id}] Failed to write file to '{path}': {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise SandboxFileOperationError(error_msg) from e

    async def read_file(self, path: str) -> str:
        """Read content from a file in the sandbox."""
        try:
            sandbox = await self.ensure_sandbox()
            logger.debug(f"[{self._session_id}] Reading file from path: {path}")

            # Run synchronous file read in thread pool
            content = await asyncio.to_thread(sandbox.files.read, path)

            logger.info(f"[{self._session_id}] Successfully read {len(content)} bytes from {path}")
            return content

        except SandboxInitializationError:
            raise
        except Exception as e:
            error_msg = f"[{self._session_id}] Failed to read file from '{path}': {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise SandboxFileOperationError(error_msg) from e

    async def run_command(self, command: str, timeout: Optional[int] = 120, background: bool = False) -> Dict[str, Any]:
        """Execute a shell command in the sandbox.

        Args:
            command: Shell command to execute
            timeout: Command timeout in seconds (default 120, use 0 for no timeout)
            background: If True, start process in background and return immediately
        """
        try:
            sandbox = await self.ensure_sandbox()
            logger.info(f"[{self._session_id}] Executing command: {command[:80]}{'...' if len(command) > 80 else ''} (timeout={timeout}s, background={background})")

            # Keep sandbox alive on activity
            await self.keep_alive()

            if background:
                # For background processes (like dev servers), use nohup and redirect output
                bg_command = f"nohup {command} > /tmp/cmd_output.log 2>&1 &"
                exec_result = await asyncio.to_thread(
                    sandbox.commands.run,
                    bg_command,
                    timeout=10  # Short timeout for background start
                )
                # Give process time to start
                await asyncio.sleep(2)
                logger.info(f"[{self._session_id}] Background process started")
                return {
                    "stdout": "Process started in background",
                    "stderr": "",
                    "exit_code": 0,
                    "success": True,
                    "background": True
                }
            else:
                # Regular command with timeout
                exec_result = await asyncio.to_thread(
                    sandbox.commands.run,
                    command,
                    timeout=timeout
                )

                result = {
                    "stdout": exec_result.stdout,
                    "stderr": exec_result.stderr,
                    "exit_code": exec_result.exit_code,
                    "success": exec_result.exit_code == 0
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

        except SandboxInitializationError:
            raise
        except Exception as e:
            error_msg = f"[{self._session_id}] Failed to execute command '{command[:50]}': {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise SandboxCommandError(error_msg) from e

    async def start_dev_server(self, project_dir: str = ".", port: int = 3000) -> Dict[str, Any]:
        """Start a development server in the background and return preview URL.

        Args:
            project_dir: Directory containing the project (default: current dir)
            port: Port to run the server on (default: 3000)

        Returns:
            Dict with preview_url and status
        """
        try:
            sandbox = await self.ensure_sandbox()

            # Start dev server in background
            command = f"cd {project_dir} && PORT={port} npm run dev"
            logger.info(f"[{self._session_id}] Starting dev server: {command}")

            # Use nohup to keep process running
            bg_command = f"nohup sh -c '{command}' > /tmp/dev_server.log 2>&1 &"
            await asyncio.to_thread(
                sandbox.commands.run,
                bg_command,
                timeout=10
            )

            # Wait for server to start
            logger.info(f"[{self._session_id}] Waiting for dev server to start...")
            await asyncio.sleep(5)

            # Check if server is running
            check_result = await asyncio.to_thread(
                sandbox.commands.run,
                f"curl -s -o /dev/null -w '%{{http_code}}' http://localhost:{port} || echo 'not ready'",
                timeout=10
            )

            # Get preview URL
            host = sandbox.get_host(port)
            preview_url = f"https://{host}"

            logger.info(f"[{self._session_id}] Dev server started, preview URL: {preview_url}")

            return {
                "success": True,
                "preview_url": preview_url,
                "port": port,
                "message": f"Dev server started on port {port}"
            }

        except Exception as e:
            error_msg = f"[{self._session_id}] Failed to start dev server: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "error": error_msg
            }

    async def list_files(self, path: str = "/home/user") -> List[str]:
        """List files in a directory in the sandbox."""
        try:
            sandbox = await self.ensure_sandbox()
            logger.debug(f"[{self._session_id}] Listing files in path: {path}")

            # Use ls command to list files
            exec_result = await asyncio.to_thread(
                sandbox.commands.run, f"ls -1 {path}"
            )

            if exec_result.exit_code != 0:
                raise SandboxFileOperationError(
                    f"Failed to list directory '{path}': {exec_result.stderr}"
                )

            # Parse output into list of files
            files = [
                line.strip()
                for line in exec_result.stdout.strip().split('\n')
                if line.strip()
            ]

            logger.info(f"[{self._session_id}] Found {len(files)} items in {path}")
            return files

        except SandboxInitializationError:
            raise
        except SandboxFileOperationError:
            raise
        except Exception as e:
            error_msg = f"[{self._session_id}] Failed to list files in '{path}': {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise SandboxFileOperationError(error_msg) from e

    async def get_preview_url(self, port: int = 3000) -> str:
        """Get the preview URL for a service running on the specified port."""
        try:
            sandbox = await self.ensure_sandbox()

            # get_host is synchronous
            host = sandbox.get_host(port)
            url = f"https://{host}"

            logger.info(f"[{self._session_id}] Generated preview URL for port {port}: {url}")
            return url

        except SandboxInitializationError:
            raise
        except Exception as e:
            error_msg = f"[{self._session_id}] Failed to get preview URL for port {port}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise SandboxError(error_msg) from e

    async def destroy(self) -> None:
        """Destroy the sandbox and cleanup resources."""
        if not self._is_initialized or self._sandbox is None:
            logger.debug(f"[{self._session_id}] Sandbox not initialized, nothing to destroy")
            return

        try:
            logger.info(f"[{self._session_id}] Destroying sandbox with ID: {self._sandbox.sandbox_id}")

            # Run synchronous kill in thread pool
            await asyncio.to_thread(self._sandbox.kill)

            self._sandbox = None
            self._is_initialized = False

            logger.info(f"[{self._session_id}] Sandbox destroyed successfully")

        except Exception as e:
            error_msg = f"[{self._session_id}] Failed to destroy sandbox: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise SandboxError(error_msg) from e

    @property
    def is_initialized(self) -> bool:
        """Check if the sandbox is currently initialized."""
        return self._is_initialized and self._sandbox is not None

    @property
    def sandbox_id(self) -> Optional[str]:
        """Get the current sandbox ID."""
        return self._sandbox.sandbox_id if self._sandbox else None

    async def keep_alive(self, timeout_seconds: int = 1800) -> bool:
        """Extend sandbox timeout to keep it alive.

        Args:
            timeout_seconds: New timeout in seconds (default: 30 minutes)

        Returns:
            True if successful, False otherwise
        """
        if not self._is_initialized or self._sandbox is None:
            return False

        try:
            await asyncio.to_thread(self._sandbox.set_timeout, timeout_seconds)
            logger.debug(f"[{self._session_id}] Sandbox timeout extended to {timeout_seconds}s")
            return True
        except Exception as e:
            logger.warning(f"[{self._session_id}] Failed to extend sandbox timeout: {e}")
            return False

    async def __aenter__(self):
        """Async context manager entry."""
        await self.ensure_sandbox()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - ensures cleanup."""
        await self.destroy()
        return False
