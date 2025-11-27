"""
E2B Sandbox Manager for lifecycle management of isolated code execution environments.

This module provides a SandboxManager class that handles the creation, management,
and cleanup of E2B sandboxes with lazy initialization and comprehensive error handling.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path

from e2b_code_interpreter import Sandbox


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

    This class provides a high-level interface for managing E2B sandboxes,
    including file operations, command execution, and preview URL generation.
    The sandbox is created lazily on first use and can be destroyed when no longer needed.

    Attributes:
        _sandbox: The E2B Sandbox instance (None until initialized)
        _template: Template name for sandbox creation
        _timeout_ms: Sandbox timeout in milliseconds
        _is_initialized: Flag indicating if sandbox has been created

    Example:
        ```python
        manager = SandboxManager()

        # Sandbox is created on first use
        await manager.write_file("/home/user/app.py", "print('Hello')")

        # Execute code
        result = await manager.run_command("python /home/user/app.py")
        print(result['stdout'])

        # Get preview URL
        url = await manager.get_preview_url(8501)

        # Cleanup
        await manager.destroy()
        ```
    """

    def __init__(self, template: str = "base", timeout_minutes: int = 15):
        """
        Initialize the SandboxManager.

        Args:
            template: E2B template name to use for sandbox creation (default: "base")
            timeout_minutes: Sandbox timeout in minutes (default: 15)
        """
        self._sandbox: Optional[Sandbox] = None
        self._template: str = template
        self._timeout_ms: int = timeout_minutes * 60 * 1000
        self._is_initialized: bool = False

        logger.info(
            f"SandboxManager initialized with template='{template}', "
            f"timeout={timeout_minutes}min"
        )

    async def ensure_sandbox(self, template: Optional[str] = None) -> Sandbox:
        """
        Ensure sandbox is created and return it (lazy initialization).

        This method creates the sandbox on first call and returns the existing
        instance on subsequent calls. It's idempotent and safe to call multiple times.

        Args:
            template: Optional template override. If provided, will use this template
                     instead of the default. Only applies on first initialization.

        Returns:
            Sandbox: The initialized E2B Sandbox instance

        Raises:
            SandboxInitializationError: If sandbox creation fails

        Example:
            ```python
            sandbox = await manager.ensure_sandbox()
            # Use sandbox directly if needed
            ```
        """
        if self._is_initialized and self._sandbox is not None:
            logger.debug("Sandbox already initialized, returning existing instance")
            return self._sandbox

        template_to_use = template or self._template

        try:
            logger.info(
                f"Creating sandbox with template='{template_to_use}', "
                f"timeout={self._timeout_ms}ms"
            )

            self._sandbox = await Sandbox.create(
                template=template_to_use,
                timeout=self._timeout_ms
            )

            self._is_initialized = True
            logger.info(f"Sandbox created successfully with ID: {self._sandbox.sandbox_id}")

            return self._sandbox

        except Exception as e:
            error_msg = f"Failed to create sandbox with template '{template_to_use}': {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise SandboxInitializationError(error_msg) from e

    async def write_file(self, path: str, content: str) -> Dict[str, Any]:
        """
        Write content to a file in the sandbox.

        Args:
            path: Absolute path where the file should be written in the sandbox
            content: File content as a string

        Returns:
            dict: Result dictionary with:
                - success (bool): Whether the operation succeeded
                - path (str): The path where the file was written
                - size (int): Size of the written content in bytes

        Raises:
            SandboxFileOperationError: If file write operation fails

        Example:
            ```python
            result = await manager.write_file(
                "/home/user/app.py",
                "import streamlit as st\\nst.write('Hello')"
            )
            print(f"Wrote {result['size']} bytes to {result['path']}")
            ```
        """
        try:
            sandbox = await self.ensure_sandbox()
            logger.debug(f"Writing file to path: {path}")

            await sandbox.files.write(path, content)

            result = {
                "success": True,
                "path": path,
                "size": len(content.encode('utf-8'))
            }

            logger.info(f"Successfully wrote {result['size']} bytes to {path}")
            return result

        except SandboxInitializationError:
            raise
        except Exception as e:
            error_msg = f"Failed to write file to '{path}': {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise SandboxFileOperationError(error_msg) from e

    async def read_file(self, path: str) -> str:
        """
        Read content from a file in the sandbox.

        Args:
            path: Absolute path to the file in the sandbox

        Returns:
            str: File content as a string

        Raises:
            SandboxFileOperationError: If file read operation fails

        Example:
            ```python
            content = await manager.read_file("/home/user/app.py")
            print(content)
            ```
        """
        try:
            sandbox = await self.ensure_sandbox()
            logger.debug(f"Reading file from path: {path}")

            content = await sandbox.files.read(path)

            logger.info(f"Successfully read {len(content)} bytes from {path}")
            return content

        except SandboxInitializationError:
            raise
        except Exception as e:
            error_msg = f"Failed to read file from '{path}': {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise SandboxFileOperationError(error_msg) from e

    async def run_command(self, command: str, timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Execute a shell command in the sandbox.

        Args:
            command: Shell command to execute
            timeout: Optional timeout in seconds (defaults to None for no timeout)

        Returns:
            dict: Command execution result with:
                - stdout (str): Standard output from the command
                - stderr (str): Standard error from the command
                - exit_code (int): Command exit code (0 indicates success)
                - success (bool): True if exit_code is 0

        Raises:
            SandboxCommandError: If command execution fails

        Example:
            ```python
            result = await manager.run_command("pip install pandas")
            if result['success']:
                print("Installation successful")
            else:
                print(f"Error: {result['stderr']}")
            ```
        """
        try:
            sandbox = await self.ensure_sandbox()
            logger.debug(f"Executing command: {command}")

            if timeout:
                exec_result = await asyncio.wait_for(
                    sandbox.commands.run(command),
                    timeout=timeout
                )
            else:
                exec_result = await sandbox.commands.run(command)

            result = {
                "stdout": exec_result.stdout,
                "stderr": exec_result.stderr,
                "exit_code": exec_result.exit_code,
                "success": exec_result.exit_code == 0
            }

            if result['success']:
                logger.info(
                    f"Command executed successfully: {command[:50]}... "
                    f"(exit_code={result['exit_code']})"
                )
            else:
                logger.warning(
                    f"Command failed: {command[:50]}... "
                    f"(exit_code={result['exit_code']}, stderr={result['stderr'][:100]})"
                )

            return result

        except asyncio.TimeoutError:
            error_msg = f"Command timed out after {timeout}s: {command}"
            logger.error(error_msg)
            raise SandboxCommandError(error_msg)
        except SandboxInitializationError:
            raise
        except Exception as e:
            error_msg = f"Failed to execute command '{command}': {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise SandboxCommandError(error_msg) from e

    async def list_files(self, path: str = "/home/user") -> List[str]:
        """
        List files in a directory in the sandbox.

        Args:
            path: Directory path to list (default: "/home/user")

        Returns:
            list: List of file/directory names in the specified path

        Raises:
            SandboxFileOperationError: If directory listing fails

        Example:
            ```python
            files = await manager.list_files("/home/user")
            for file in files:
                print(file)
            ```
        """
        try:
            sandbox = await self.ensure_sandbox()
            logger.debug(f"Listing files in path: {path}")

            # Use ls command to list files
            result = await sandbox.commands.run(f"ls -1 {path}")

            if result.exit_code != 0:
                raise SandboxFileOperationError(
                    f"Failed to list directory '{path}': {result.stderr}"
                )

            # Parse output into list of files
            files = [
                line.strip()
                for line in result.stdout.strip().split('\n')
                if line.strip()
            ]

            logger.info(f"Found {len(files)} items in {path}")
            return files

        except SandboxInitializationError:
            raise
        except SandboxFileOperationError:
            raise
        except Exception as e:
            error_msg = f"Failed to list files in '{path}': {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise SandboxFileOperationError(error_msg) from e

    async def get_preview_url(self, port: int = 3000) -> str:
        """
        Get the preview URL for a service running on the specified port.

        This generates a publicly accessible URL for services running inside the sandbox,
        commonly used for web applications like Streamlit (port 8501), React dev servers
        (port 3000), or other web services.

        Args:
            port: Port number where the service is running (default: 3000)

        Returns:
            str: Public HTTPS URL to access the service

        Raises:
            SandboxInitializationError: If sandbox is not initialized

        Example:
            ```python
            # Start a Streamlit app
            await manager.run_command("streamlit run app.py --server.port 8501 &")

            # Get the preview URL
            url = await manager.get_preview_url(8501)
            print(f"App available at: {url}")
            ```
        """
        try:
            sandbox = await self.ensure_sandbox()

            host = sandbox.get_host(port)
            url = f"https://{host}"

            logger.info(f"Generated preview URL for port {port}: {url}")
            return url

        except SandboxInitializationError:
            raise
        except Exception as e:
            error_msg = f"Failed to get preview URL for port {port}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise SandboxError(error_msg) from e

    async def destroy(self) -> None:
        """
        Destroy the sandbox and cleanup resources.

        This method should be called when the sandbox is no longer needed to free up
        resources. It's idempotent and safe to call multiple times.

        Raises:
            SandboxError: If sandbox destruction fails

        Example:
            ```python
            try:
                # Use sandbox...
                await manager.write_file("/home/user/app.py", "...")
            finally:
                # Always cleanup
                await manager.destroy()
            ```
        """
        if not self._is_initialized or self._sandbox is None:
            logger.debug("Sandbox not initialized, nothing to destroy")
            return

        try:
            logger.info(f"Destroying sandbox with ID: {self._sandbox.sandbox_id}")

            await self._sandbox.kill()

            self._sandbox = None
            self._is_initialized = False

            logger.info("Sandbox destroyed successfully")

        except Exception as e:
            error_msg = f"Failed to destroy sandbox: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise SandboxError(error_msg) from e

    @property
    def is_initialized(self) -> bool:
        """
        Check if the sandbox is currently initialized.

        Returns:
            bool: True if sandbox is initialized and ready to use

        Example:
            ```python
            if manager.is_initialized:
                print("Sandbox is ready")
            else:
                print("Sandbox needs initialization")
            ```
        """
        return self._is_initialized and self._sandbox is not None

    @property
    def sandbox_id(self) -> Optional[str]:
        """
        Get the current sandbox ID.

        Returns:
            str or None: Sandbox ID if initialized, None otherwise

        Example:
            ```python
            if manager.sandbox_id:
                print(f"Current sandbox: {manager.sandbox_id}")
            ```
        """
        return self._sandbox.sandbox_id if self._sandbox else None

    async def __aenter__(self):
        """
        Async context manager entry.

        Example:
            ```python
            async with SandboxManager() as manager:
                await manager.write_file("/home/user/app.py", "...")
                # Sandbox is automatically destroyed on exit
            ```
        """
        await self.ensure_sandbox()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - ensures cleanup."""
        await self.destroy()
        return False
