"""
Tests for path traversal protection in LocalSandboxManager.
"""

import pytest
import sys
import tempfile
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.local_sandbox_manager import LocalSandboxManager, LocalSandboxFileOperationError


class TestPathResolution:
    """Test path resolution and traversal protection."""

    @pytest.fixture
    def sandbox_with_dir(self, temp_sandbox):
        """Create a LocalSandboxManager with temp directory set."""
        manager = LocalSandboxManager(session_id="test-session")
        manager._project_dir = temp_sandbox
        manager._is_initialized = True
        return manager, temp_sandbox

    def test_relative_path_stays_in_sandbox(self, sandbox_with_dir):
        """Relative paths should resolve within sandbox."""
        manager, temp_sandbox = sandbox_with_dir
        result = manager._resolve_path(temp_sandbox, "app/page.tsx")
        assert str(result).startswith(str(temp_sandbox))
        assert result == temp_sandbox / "app/page.tsx"

    def test_nested_relative_path(self, sandbox_with_dir):
        """Nested relative paths should work."""
        manager, temp_sandbox = sandbox_with_dir
        result = manager._resolve_path(temp_sandbox, "src/components/Button.tsx")
        assert result == temp_sandbox / "src/components/Button.tsx"

    def test_absolute_path_inside_sandbox(self, sandbox_with_dir):
        """Absolute paths inside sandbox should be allowed."""
        manager, temp_sandbox = sandbox_with_dir
        absolute_path = temp_sandbox / "components" / "Header.tsx"
        result = manager._resolve_path(temp_sandbox, str(absolute_path))
        # Result should be inside sandbox
        assert str(result.resolve()).startswith(str(temp_sandbox.resolve()))

    def test_blocks_parent_directory_traversal(self, sandbox_with_dir):
        """Should block ../ traversal attempts."""
        manager, temp_sandbox = sandbox_with_dir
        with pytest.raises(LocalSandboxFileOperationError) as exc_info:
            manager._resolve_path(temp_sandbox, "../../../etc/passwd")
        assert "traversal" in str(exc_info.value).lower()

    def test_blocks_double_dot_in_path(self, sandbox_with_dir):
        """Should block paths with .. that escape sandbox."""
        manager, temp_sandbox = sandbox_with_dir
        with pytest.raises(LocalSandboxFileOperationError) as exc_info:
            manager._resolve_path(temp_sandbox, "app/../../../etc/passwd")
        assert "traversal" in str(exc_info.value).lower()

    def test_absolute_path_outside_sandbox_treated_as_relative(self, sandbox_with_dir):
        """Absolute paths outside sandbox are treated as relative (stripped of leading /)."""
        manager, temp_sandbox = sandbox_with_dir
        # Absolute paths outside sandbox are converted to relative
        result = manager._resolve_path(temp_sandbox, "/etc/passwd")
        # Should be treated as relative: sandbox/etc/passwd
        assert str(result).startswith(str(temp_sandbox))
        assert "etc/passwd" in str(result)

    def test_home_directory_path_treated_as_relative(self, sandbox_with_dir):
        """Home directory paths are treated as relative."""
        manager, temp_sandbox = sandbox_with_dir
        home_path = str(Path.home() / ".ssh" / "id_rsa")
        # Should be treated as relative path within sandbox
        result = manager._resolve_path(temp_sandbox, home_path)
        assert str(result).startswith(str(temp_sandbox))

    def test_allows_dot_files_in_sandbox(self, sandbox_with_dir):
        """Should allow dot files within sandbox."""
        manager, temp_sandbox = sandbox_with_dir
        result = manager._resolve_path(temp_sandbox, ".gitignore")
        assert result == temp_sandbox / ".gitignore"

    def test_allows_deep_nested_paths(self, sandbox_with_dir):
        """Should allow deeply nested paths within sandbox."""
        manager, temp_sandbox = sandbox_with_dir
        result = manager._resolve_path(
            temp_sandbox,
            "src/features/auth/components/LoginForm/LoginForm.tsx"
        )
        assert str(result).startswith(str(temp_sandbox))

    def test_handles_trailing_slashes(self, sandbox_with_dir):
        """Should handle paths with trailing slashes."""
        manager, temp_sandbox = sandbox_with_dir
        result = manager._resolve_path(temp_sandbox, "components/")
        assert str(result).startswith(str(temp_sandbox))


class TestSandboxInitialization:
    """Test sandbox directory initialization."""

    @pytest.mark.asyncio
    async def test_creates_sandbox_directory(self):
        """Sandbox should create project directory on ensure_sandbox."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = LocalSandboxManager(
                session_id="test-init-session"
            )
            # Override the base path for testing
            manager._project_dir = Path(tmpdir) / "test-project"

            # Directory should not exist yet
            assert not manager._project_dir.exists()

            # Calling ensure_sandbox should create it
            await manager.ensure_sandbox()

            # Now it should exist
            assert manager._project_dir.exists()
            assert manager._project_dir.is_dir()


class TestFileOperations:
    """Test file read/write operations with path security."""

    @pytest.fixture
    async def initialized_sandbox(self, temp_sandbox):
        """Create and initialize a sandbox."""
        manager = LocalSandboxManager(
            session_id="test-file-ops"
        )
        manager._project_dir = temp_sandbox
        manager._is_initialized = True
        return manager

    @pytest.mark.asyncio
    async def test_write_file_creates_parent_dirs(self, initialized_sandbox, temp_sandbox):
        """Writing to nested path should create parent directories."""
        await initialized_sandbox.write_file(
            "src/components/Button.tsx",
            "export const Button = () => <button>Click</button>"
        )

        file_path = temp_sandbox / "src" / "components" / "Button.tsx"
        assert file_path.exists()
        assert file_path.read_text() == "export const Button = () => <button>Click</button>"

    @pytest.mark.asyncio
    async def test_read_file_returns_content(self, initialized_sandbox, temp_sandbox):
        """Should read file content correctly."""
        # Create a file first
        test_content = "Hello, World!"
        (temp_sandbox / "test.txt").write_text(test_content)

        result = await initialized_sandbox.read_file("test.txt")
        # read_file returns the content directly as string
        assert result == test_content

    @pytest.mark.asyncio
    async def test_write_file_blocks_traversal(self, initialized_sandbox):
        """Writing outside sandbox should fail."""
        with pytest.raises(LocalSandboxFileOperationError):
            await initialized_sandbox.write_file(
                "../../../tmp/evil.txt",
                "malicious content"
            )

    @pytest.mark.asyncio
    async def test_read_file_blocks_traversal(self, initialized_sandbox):
        """Reading outside sandbox should fail."""
        with pytest.raises(LocalSandboxFileOperationError):
            await initialized_sandbox.read_file("../../../etc/passwd")


class TestListFiles:
    """Test directory listing with security."""

    @pytest.fixture
    async def sandbox_with_files(self, temp_sandbox):
        """Create sandbox with some test files."""
        manager = LocalSandboxManager(session_id="test-list")
        manager._project_dir = temp_sandbox
        manager._is_initialized = True

        # Create some test files
        (temp_sandbox / "file1.txt").write_text("content1")
        (temp_sandbox / "file2.tsx").write_text("content2")
        (temp_sandbox / "subdir").mkdir()
        (temp_sandbox / "subdir" / "file3.ts").write_text("content3")

        return manager

    @pytest.mark.asyncio
    async def test_list_root_directory(self, sandbox_with_files, temp_sandbox):
        """Should list files in root directory."""
        result = await sandbox_with_files.list_files(".")

        # list_files returns a list of file names (strings)
        assert "file1.txt" in result
        assert "file2.tsx" in result
        assert "subdir" in result

    @pytest.mark.asyncio
    async def test_list_subdirectory(self, sandbox_with_files):
        """Should list files in subdirectory."""
        result = await sandbox_with_files.list_files("subdir")

        # list_files returns a list of file names (strings)
        assert "file3.ts" in result

    @pytest.mark.asyncio
    async def test_list_blocks_traversal(self, sandbox_with_files):
        """Should block listing outside sandbox."""
        with pytest.raises(LocalSandboxFileOperationError):
            await sandbox_with_files.list_files("../../../")
