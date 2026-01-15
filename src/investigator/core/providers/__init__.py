"""
Git hosting provider abstractions for GitHub, GitLab, etc.
"""

from .base_provider import GitProvider
from .github_provider import GitHubProvider
from .gitlab_provider import GitLabProvider
from .provider_factory import get_provider, get_provider_for_url

__all__ = [
    "GitProvider",
    "GitHubProvider",
    "GitLabProvider",
    "get_provider",
    "get_provider_for_url",
]
