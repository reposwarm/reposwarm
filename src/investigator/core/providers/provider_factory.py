"""
Factory function for creating Git provider instances.
"""

import os
from typing import Optional
from urllib.parse import urlparse

from .base_provider import GitProvider
from .github_provider import GitHubProvider
from .gitlab_provider import GitLabProvider


def get_provider(
    repo_url: Optional[str] = None,
    provider_type: Optional[str] = None,
    token: Optional[str] = None,
    base_url: Optional[str] = None
) -> GitProvider:
    """
    Factory function to get the appropriate Git provider.

    Detection priority:
    1. Explicit provider_type parameter
    2. GIT_PROVIDER environment variable
    3. URL-based detection
    4. Default to GitHub

    Args:
        repo_url: Repository URL (used for auto-detection)
        provider_type: Explicit provider type ("github" or "gitlab")
        token: Authentication token (auto-detected from env if not provided)
        base_url: Base URL for self-hosted instances

    Returns:
        GitProvider instance
    """
    # Check explicit provider type first
    if not provider_type:
        provider_type = os.getenv("GIT_PROVIDER", "").lower()

    # URL-based detection if no explicit type
    if not provider_type and repo_url:
        provider_type = _detect_provider_from_url(repo_url)

    # Default to GitHub if still not determined
    if not provider_type:
        provider_type = "github"

    # Get appropriate token from environment if not provided
    if not token:
        if provider_type == "gitlab":
            token = os.getenv("GITLAB_TOKEN")
        else:
            token = os.getenv("GITHUB_TOKEN")

    # Get base URL for self-hosted instances if not provided
    if not base_url:
        if provider_type == "gitlab":
            base_url = os.getenv("GITLAB_BASE_URL")
        # GitHub Enterprise support could be added here

    # Instantiate and return the appropriate provider
    if provider_type == "gitlab":
        return GitLabProvider(token=token, base_url=base_url)
    else:
        return GitHubProvider(token=token, base_url=base_url)


def _detect_provider_from_url(url: str) -> str:
    """
    Detect provider type from repository URL.

    Args:
        url: Repository URL

    Returns:
        Provider type ("github" or "gitlab")
    """
    if not url:
        return "github"

    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()

    # Check for GitLab
    if "gitlab" in hostname:
        return "gitlab"

    # Check for GitHub
    if "github" in hostname:
        return "github"

    # Check environment for hints about self-hosted instances
    gitlab_base = os.getenv("GITLAB_BASE_URL", "")
    if gitlab_base and gitlab_base in url:
        return "gitlab"

    # Default to GitHub
    return "github"


def get_provider_for_url(repo_url: str) -> GitProvider:
    """
    Convenience function to get a provider based solely on URL.

    This auto-detects the provider from the URL and gets the
    appropriate token from environment variables.

    Args:
        repo_url: Repository URL

    Returns:
        GitProvider instance configured for the URL
    """
    return get_provider(repo_url=repo_url)
