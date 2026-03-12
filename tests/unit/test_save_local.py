"""Tests for the local file save mode of save_to_arch_hub."""

import os
import sys
import pytest
import tempfile
from unittest.mock import patch, MagicMock, PropertyMock

# Add src to path so we can import activities
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))


# Mock the temporalio activity module before importing
mock_activity = MagicMock()
mock_activity.logger = MagicMock()
mock_activity.heartbeat = MagicMock()
mock_activity.defn = lambda f: f  # passthrough decorator

mock_temporalio = MagicMock()
mock_temporalio.activity = mock_activity

sys.modules['temporalio'] = mock_temporalio
sys.modules['temporalio.activity'] = mock_activity


from activities.investigate_activities import _save_to_arch_hub_local, save_to_arch_hub


PATCH_TARGET = "investigator.core.config.Config"


class TestSaveToArchHubLocal:
    """Tests for _save_to_arch_hub_local function."""

    @pytest.fixture
    def sample_arch_files(self):
        return [
            {
                "repo_name": "my-app",
                "arch_file_content": "# Architecture\n\nThis is the architecture of my-app."
            },
            {
                "repo_name": "my-lib",
                "arch_file_content": "# Architecture\n\nThis is the architecture of my-lib."
            },
        ]

    @pytest.mark.asyncio
    async def test_saves_files_to_local_directory(self, sample_arch_files):
        """Test that arch files are written to the local path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch(f"{PATCH_TARGET}.ARCH_HUB_LOCAL_PATH", tmpdir), \
                 patch(f"{PATCH_TARGET}.ARCH_HUB_FILES_DIR", ""):

                result = await _save_to_arch_hub_local(sample_arch_files)

            assert result["status"] == "success"
            assert len(result["files_saved"]) == 2
            assert "my-app.arch.md" in result["files_saved"]
            assert "my-lib.arch.md" in result["files_saved"]
            assert result["local_path"] == tmpdir

            # Verify files actually exist with correct content
            app_path = os.path.join(tmpdir, "my-app.arch.md")
            lib_path = os.path.join(tmpdir, "my-lib.arch.md")
            assert os.path.isfile(app_path)
            assert os.path.isfile(lib_path)

            with open(app_path, 'r') as f:
                assert f.read() == "# Architecture\n\nThis is the architecture of my-app."

    @pytest.mark.asyncio
    async def test_creates_subdirectory_when_files_dir_set(self, sample_arch_files):
        """Test that ARCH_HUB_FILES_DIR creates a subdirectory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch(f"{PATCH_TARGET}.ARCH_HUB_LOCAL_PATH", tmpdir), \
                 patch(f"{PATCH_TARGET}.ARCH_HUB_FILES_DIR", "docs/arch"):

                result = await _save_to_arch_hub_local(sample_arch_files)

            assert result["status"] == "success"
            assert len(result["files_saved"]) == 2

            # Files should be inside the subdirectory
            subdir = os.path.join(tmpdir, "docs", "arch")
            assert os.path.isdir(subdir)
            assert os.path.isfile(os.path.join(subdir, "my-app.arch.md"))
            assert os.path.isfile(os.path.join(subdir, "my-lib.arch.md"))

    @pytest.mark.asyncio
    async def test_returns_error_when_local_path_empty(self):
        """Test that an error is returned when ARCH_HUB_LOCAL_PATH is empty."""
        with patch(f"{PATCH_TARGET}.ARCH_HUB_LOCAL_PATH", ""), \
             patch(f"{PATCH_TARGET}.ARCH_HUB_FILES_DIR", ""):

            result = await _save_to_arch_hub_local([{"repo_name": "x", "arch_file_content": "y"}])

        assert result["status"] == "error"
        assert "ARCH_HUB_LOCAL_PATH not set" in result["message"]

    @pytest.mark.asyncio
    async def test_skips_entries_without_repo_name(self):
        """Test that entries without repo_name are skipped."""
        arch_files = [
            {"repo_name": "", "arch_file_content": "some content"},
            {"repo_name": "valid-repo", "arch_file_content": "valid content"},
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch(f"{PATCH_TARGET}.ARCH_HUB_LOCAL_PATH", tmpdir), \
                 patch(f"{PATCH_TARGET}.ARCH_HUB_FILES_DIR", ""):

                result = await _save_to_arch_hub_local(arch_files)

            assert result["status"] == "success"
            assert result["files_saved"] == ["valid-repo.arch.md"]
            assert not os.path.exists(os.path.join(tmpdir, ".arch.md"))

    @pytest.mark.asyncio
    async def test_skips_entries_without_content(self):
        """Test that entries without arch_file_content are skipped."""
        arch_files = [
            {"repo_name": "empty-repo", "arch_file_content": ""},
            {"repo_name": "good-repo", "arch_file_content": "has content"},
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch(f"{PATCH_TARGET}.ARCH_HUB_LOCAL_PATH", tmpdir), \
                 patch(f"{PATCH_TARGET}.ARCH_HUB_FILES_DIR", ""):

                result = await _save_to_arch_hub_local(arch_files)

            assert result["status"] == "success"
            assert result["files_saved"] == ["good-repo.arch.md"]

    @pytest.mark.asyncio
    async def test_returns_completed_when_no_files_saved(self):
        """Test that 'completed' status is returned when all entries are skipped."""
        arch_files = [
            {"repo_name": "", "arch_file_content": ""},
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch(f"{PATCH_TARGET}.ARCH_HUB_LOCAL_PATH", tmpdir), \
                 patch(f"{PATCH_TARGET}.ARCH_HUB_FILES_DIR", ""):

                result = await _save_to_arch_hub_local(arch_files)

            assert result["status"] == "completed"
            assert result["files_saved"] == []

    @pytest.mark.asyncio
    async def test_creates_local_path_if_not_exists(self, sample_arch_files):
        """Test that the local path directory is created if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            new_path = os.path.join(tmpdir, "new", "nested", "dir")
            assert not os.path.exists(new_path)

            with patch(f"{PATCH_TARGET}.ARCH_HUB_LOCAL_PATH", new_path), \
                 patch(f"{PATCH_TARGET}.ARCH_HUB_FILES_DIR", ""):

                result = await _save_to_arch_hub_local(sample_arch_files)

            assert result["status"] == "success"
            assert os.path.isdir(new_path)
            assert os.path.isfile(os.path.join(new_path, "my-app.arch.md"))


class TestSaveToArchHubSkipUnconfigured:
    """Tests for skipping arch-hub save when not configured."""

    @pytest.mark.asyncio
    async def test_skips_when_default_placeholder_url(self):
        """Test that save is skipped when ARCH_HUB_BASE_URL is the default placeholder."""
        with patch(f"{PATCH_TARGET}.ARCH_HUB_MODE", "git"), \
             patch(f"{PATCH_TARGET}.ARCH_HUB_BASE_URL", "https://github.com/your-org"):

            result = await save_to_arch_hub([{"repo_name": "test", "arch_file_content": "content"}])

        assert result["status"] == "skipped"
        assert "not configured" in result["message"]
        assert result["files_saved"] == []

    @pytest.mark.asyncio
    async def test_skips_when_empty_base_url(self):
        """Test that save is skipped when ARCH_HUB_BASE_URL is empty."""
        with patch(f"{PATCH_TARGET}.ARCH_HUB_MODE", "git"), \
             patch(f"{PATCH_TARGET}.ARCH_HUB_BASE_URL", ""):

            result = await save_to_arch_hub([{"repo_name": "test", "arch_file_content": "content"}])

        assert result["status"] == "skipped"
        assert "not configured" in result["message"]

    @pytest.mark.asyncio
    async def test_dispatches_to_local_mode(self):
        """Test that local mode is dispatched correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch(f"{PATCH_TARGET}.ARCH_HUB_MODE", "local"), \
                 patch(f"{PATCH_TARGET}.ARCH_HUB_LOCAL_PATH", tmpdir), \
                 patch(f"{PATCH_TARGET}.ARCH_HUB_FILES_DIR", ""):

                result = await save_to_arch_hub([{"repo_name": "test", "arch_file_content": "content"}])

            assert result["status"] == "success"
            assert os.path.isfile(os.path.join(tmpdir, "test.arch.md"))
