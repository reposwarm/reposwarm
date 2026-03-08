"""
Unit tests for Config class URL construction methods.
Tests smart arch-hub URL construction logic.
"""

import pytest
import os
from unittest.mock import patch
import sys

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src'))

from investigator.core.config import Config


class TestArchHubURLConstruction:
    """Tests for smart arch-hub URL construction methods."""

    def test_get_arch_hub_repo_url_with_org_url(self):
        """Test that org URL (2 segments) appends repo name with .git."""
        with patch.dict(os.environ, {
            'ARCH_HUB_BASE_URL': 'https://github.com/reposwarm',
            'ARCH_HUB_REPO_NAME': 'architecture-hub'
        }, clear=True):
            # Force reload of Config values
            Config.ARCH_HUB_BASE_URL = os.getenv("ARCH_HUB_BASE_URL", "https://github.com/your-org")
            Config.ARCH_HUB_REPO_NAME = os.getenv("ARCH_HUB_REPO_NAME", "architecture-hub")

            result = Config.get_arch_hub_repo_url()

            assert result == "https://github.com/reposwarm/architecture-hub.git"

    def test_get_arch_hub_repo_url_with_full_repo_url(self):
        """Test that full repo URL (3+ segments) is used directly with .git."""
        with patch.dict(os.environ, {
            'ARCH_HUB_BASE_URL': 'https://github.com/reposwarm/e2e-arch-hub',
            'ARCH_HUB_REPO_NAME': 'architecture-hub'
        }, clear=True):
            Config.ARCH_HUB_BASE_URL = os.getenv("ARCH_HUB_BASE_URL", "https://github.com/your-org")
            Config.ARCH_HUB_REPO_NAME = os.getenv("ARCH_HUB_REPO_NAME", "architecture-hub")

            result = Config.get_arch_hub_repo_url()

            assert result == "https://github.com/reposwarm/e2e-arch-hub.git"

    def test_get_arch_hub_repo_url_with_full_repo_url_already_has_git(self):
        """Test that .git is not duplicated if already present."""
        with patch.dict(os.environ, {
            'ARCH_HUB_BASE_URL': 'https://github.com/reposwarm/e2e-arch-hub.git',
            'ARCH_HUB_REPO_NAME': 'architecture-hub'
        }, clear=True):
            Config.ARCH_HUB_BASE_URL = os.getenv("ARCH_HUB_BASE_URL", "https://github.com/your-org")
            Config.ARCH_HUB_REPO_NAME = os.getenv("ARCH_HUB_REPO_NAME", "architecture-hub")

            result = Config.get_arch_hub_repo_url()

            assert result == "https://github.com/reposwarm/e2e-arch-hub.git"

    def test_get_arch_hub_repo_url_with_trailing_slash(self):
        """Test that trailing slashes are handled correctly."""
        with patch.dict(os.environ, {
            'ARCH_HUB_BASE_URL': 'https://github.com/reposwarm/',
            'ARCH_HUB_REPO_NAME': 'architecture-hub'
        }, clear=True):
            Config.ARCH_HUB_BASE_URL = os.getenv("ARCH_HUB_BASE_URL", "https://github.com/your-org")
            Config.ARCH_HUB_REPO_NAME = os.getenv("ARCH_HUB_REPO_NAME", "architecture-hub")

            result = Config.get_arch_hub_repo_url()

            assert result == "https://github.com/reposwarm/architecture-hub.git"

    def test_get_arch_hub_repo_url_without_protocol(self):
        """Test URL construction works without https:// protocol."""
        with patch.dict(os.environ, {
            'ARCH_HUB_BASE_URL': 'github.com/reposwarm',
            'ARCH_HUB_REPO_NAME': 'architecture-hub'
        }, clear=True):
            Config.ARCH_HUB_BASE_URL = os.getenv("ARCH_HUB_BASE_URL", "https://github.com/your-org")
            Config.ARCH_HUB_REPO_NAME = os.getenv("ARCH_HUB_REPO_NAME", "architecture-hub")

            result = Config.get_arch_hub_repo_url()

            assert result == "github.com/reposwarm/architecture-hub.git"

    def test_get_arch_hub_repo_url_with_deep_path(self):
        """Test that URLs with 3+ path segments are treated as full repo URLs."""
        with patch.dict(os.environ, {
            'ARCH_HUB_BASE_URL': 'https://gitlab.com/group/subgroup/my-arch-hub',
            'ARCH_HUB_REPO_NAME': 'architecture-hub'
        }, clear=True):
            Config.ARCH_HUB_BASE_URL = os.getenv("ARCH_HUB_BASE_URL", "https://github.com/your-org")
            Config.ARCH_HUB_REPO_NAME = os.getenv("ARCH_HUB_REPO_NAME", "architecture-hub")

            result = Config.get_arch_hub_repo_url()

            # Should use the full URL directly, not append architecture-hub
            assert result == "https://gitlab.com/group/subgroup/my-arch-hub.git"

    def test_get_arch_hub_web_url_with_org_url(self):
        """Test that org URL (2 segments) appends repo name without .git."""
        with patch.dict(os.environ, {
            'ARCH_HUB_BASE_URL': 'https://github.com/reposwarm',
            'ARCH_HUB_REPO_NAME': 'architecture-hub'
        }, clear=True):
            Config.ARCH_HUB_BASE_URL = os.getenv("ARCH_HUB_BASE_URL", "https://github.com/your-org")
            Config.ARCH_HUB_REPO_NAME = os.getenv("ARCH_HUB_REPO_NAME", "architecture-hub")

            result = Config.get_arch_hub_web_url()

            assert result == "https://github.com/reposwarm/architecture-hub"

    def test_get_arch_hub_web_url_with_full_repo_url(self):
        """Test that full repo URL (3+ segments) is used directly without .git."""
        with patch.dict(os.environ, {
            'ARCH_HUB_BASE_URL': 'https://github.com/reposwarm/e2e-arch-hub',
            'ARCH_HUB_REPO_NAME': 'architecture-hub'
        }, clear=True):
            Config.ARCH_HUB_BASE_URL = os.getenv("ARCH_HUB_BASE_URL", "https://github.com/your-org")
            Config.ARCH_HUB_REPO_NAME = os.getenv("ARCH_HUB_REPO_NAME", "architecture-hub")

            result = Config.get_arch_hub_web_url()

            assert result == "https://github.com/reposwarm/e2e-arch-hub"

    def test_get_arch_hub_web_url_removes_git_extension(self):
        """Test that .git extension is removed from web URL."""
        with patch.dict(os.environ, {
            'ARCH_HUB_BASE_URL': 'https://github.com/reposwarm/e2e-arch-hub.git',
            'ARCH_HUB_REPO_NAME': 'architecture-hub'
        }, clear=True):
            Config.ARCH_HUB_BASE_URL = os.getenv("ARCH_HUB_BASE_URL", "https://github.com/your-org")
            Config.ARCH_HUB_REPO_NAME = os.getenv("ARCH_HUB_REPO_NAME", "architecture-hub")

            result = Config.get_arch_hub_web_url()

            assert result == "https://github.com/reposwarm/e2e-arch-hub"

    def test_get_arch_hub_web_url_with_trailing_slash(self):
        """Test that trailing slashes are handled correctly in web URLs."""
        with patch.dict(os.environ, {
            'ARCH_HUB_BASE_URL': 'https://github.com/reposwarm/',
            'ARCH_HUB_REPO_NAME': 'architecture-hub'
        }, clear=True):
            Config.ARCH_HUB_BASE_URL = os.getenv("ARCH_HUB_BASE_URL", "https://github.com/your-org")
            Config.ARCH_HUB_REPO_NAME = os.getenv("ARCH_HUB_REPO_NAME", "architecture-hub")

            result = Config.get_arch_hub_web_url()

            assert result == "https://github.com/reposwarm/architecture-hub"
