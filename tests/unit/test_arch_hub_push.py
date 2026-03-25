"""
Tests for arch-hub push branch detection.

Verifies that save_to_arch_hub uses the current branch instead of
hardcoding "main" when pushing to the arch-hub repository.
"""

import os
import sys
import tempfile
import subprocess
from unittest.mock import MagicMock, patch, call

import pytest

# Add src to path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from investigator.core.git_manager import GitRepositoryManager


PATCH_CONFIG = "investigator.core.config.Config"


class TestGetCurrentBranch:
    """Tests for GitRepositoryManager.get_current_branch()."""

    def setup_method(self):
        self.logger = MagicMock()
        self.git_manager = GitRepositoryManager(self.logger)

    @patch("investigator.core.git_manager.subprocess.run")
    def test_get_current_branch_returns_main(self, mock_run):
        """When repo is on 'main', get_current_branch returns 'main'."""
        mock_run.return_value = MagicMock(returncode=0, stdout="main\n")
        result = self.git_manager.get_current_branch("/fake/repo")
        assert result == "main"
        mock_run.assert_called_once_with(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd="/fake/repo",
            capture_output=True,
            text=True,
        )

    @patch("investigator.core.git_manager.subprocess.run")
    def test_get_current_branch_returns_master(self, mock_run):
        """When repo is on 'master', get_current_branch returns 'master'."""
        mock_run.return_value = MagicMock(returncode=0, stdout="master\n")
        result = self.git_manager.get_current_branch("/fake/repo")
        assert result == "master"

    @patch("investigator.core.git_manager.subprocess.run")
    def test_get_current_branch_fallback_on_error(self, mock_run):
        """When git command fails, returns 'main' as default."""
        mock_run.return_value = MagicMock(returncode=128, stdout="", stderr="fatal: not a git repo")
        result = self.git_manager.get_current_branch("/fake/repo")
        assert result == "main"

    @patch("investigator.core.git_manager.subprocess.run")
    def test_get_current_branch_detached_head(self, mock_run):
        """When in detached HEAD state, git rev-parse returns 'HEAD'."""
        mock_run.return_value = MagicMock(returncode=0, stdout="HEAD\n")
        result = self.git_manager.get_current_branch("/fake/repo")
        assert result == "HEAD"


def _clone_side_effect_factory(repo_dir_path):
    """Create a side_effect for clone_or_update that creates the directory."""
    def _clone_side_effect(url, path):
        os.makedirs(path, exist_ok=True)
        return path
    return _clone_side_effect


class TestSaveToArchHubBranchDetection:
    """Tests that save_to_arch_hub uses detected branch for push."""

    def _make_mock_git_manager(self, branch="master"):
        """Create a mock GitRepositoryManager with the given current branch."""
        mock = MagicMock()
        mock.validate_github_token.return_value = {"status": "valid", "message": "ok", "user": "test"}
        mock.check_repository_permissions.return_value = {"status": "allowed", "message": "ok"}
        mock.get_current_branch.return_value = branch
        mock.push_with_authentication.return_value = {"status": "success", "message": "pushed"}
        # clone_or_update should create the directory
        mock.clone_or_update.side_effect = lambda url, path: (os.makedirs(path, exist_ok=True) or path)
        return mock

    @pytest.mark.asyncio
    async def test_save_to_arch_hub_uses_current_branch(self):
        """Push should use the detected current branch, not hardcoded 'main'.

        When the arch-hub repo's default branch is 'master', push_with_authentication
        must be called with 'master' — not the hardcoded 'main'.
        """
        from activities.investigate_activities import save_to_arch_hub

        mock_git_manager = self._make_mock_git_manager(branch="master")

        with patch(f"{PATCH_CONFIG}.ARCH_HUB_MODE", "git"), \
             patch(f"{PATCH_CONFIG}.ARCH_HUB_BASE_URL", "https://github.com/myorg"), \
             patch(f"{PATCH_CONFIG}.get_arch_hub_repo_url", return_value="https://github.com/myorg/arch-hub.git"), \
             patch(f"{PATCH_CONFIG}.ARCH_HUB_REPO_NAME", "arch-hub"), \
             patch(f"{PATCH_CONFIG}.ARCH_HUB_FILES_DIR", ""), \
             patch("investigator.core.git_manager.GitRepositoryManager", return_value=mock_git_manager), \
             patch("subprocess.run") as mock_subproc:

            # subprocess.run for git add and git commit
            mock_subproc.return_value = MagicMock(
                returncode=0,
                stdout="[master abc1234] Update test-repo.arch.md",
                stderr="",
            )

            arch_files = [{"repo_name": "test-repo", "arch_file_content": "# Architecture\nContent"}]
            result = await save_to_arch_hub(arch_files)

        # Key assertion: push must be called with "master", not "main"
        mock_git_manager.push_with_authentication.assert_called_once()
        push_args = mock_git_manager.push_with_authentication.call_args
        # push_with_authentication(repo_dir, branch)
        actual_branch = push_args[0][1] if len(push_args[0]) > 1 else push_args[1].get("branch")
        assert actual_branch == "master", (
            f"Expected push to branch 'master', got '{actual_branch}'. "
            "The push is still hardcoded to 'main'!"
        )

    @pytest.mark.asyncio
    async def test_save_to_arch_hub_empty_repo_creates_branch(self):
        """When repo is empty (detached HEAD), should create 'main' branch and push to it."""
        from activities.investigate_activities import save_to_arch_hub

        mock_git_manager = self._make_mock_git_manager(branch="HEAD")

        with patch(f"{PATCH_CONFIG}.ARCH_HUB_MODE", "git"), \
             patch(f"{PATCH_CONFIG}.ARCH_HUB_BASE_URL", "https://github.com/myorg"), \
             patch(f"{PATCH_CONFIG}.get_arch_hub_repo_url", return_value="https://github.com/myorg/arch-hub.git"), \
             patch(f"{PATCH_CONFIG}.ARCH_HUB_REPO_NAME", "arch-hub"), \
             patch(f"{PATCH_CONFIG}.ARCH_HUB_FILES_DIR", ""), \
             patch("investigator.core.git_manager.GitRepositoryManager", return_value=mock_git_manager), \
             patch("subprocess.run") as mock_subproc:

            mock_subproc.return_value = MagicMock(returncode=0, stdout="", stderr="")

            arch_files = [{"repo_name": "test-repo", "arch_file_content": "# Architecture\nContent"}]
            result = await save_to_arch_hub(arch_files)

        # Should have called git checkout -b main for empty repos
        checkout_calls = [
            c for c in mock_subproc.call_args_list
            if len(c[0]) > 0 and isinstance(c[0][0], list) and "checkout" in c[0][0]
        ]
        assert len(checkout_calls) > 0, (
            "Expected 'git checkout -b main' call for empty repo (detached HEAD), "
            "but no checkout call was made."
        )

        # Push should use "main" (the created branch)
        mock_git_manager.push_with_authentication.assert_called_once()
        push_args = mock_git_manager.push_with_authentication.call_args
        actual_branch = push_args[0][1] if len(push_args[0]) > 1 else push_args[1].get("branch")
        assert actual_branch == "main", (
            f"Expected push to branch 'main' for empty repo, got '{actual_branch}'"
        )
