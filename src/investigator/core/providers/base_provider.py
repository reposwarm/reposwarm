"""
Abstract base class for Git hosting providers (GitHub, GitLab, etc.).
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from urllib.parse import urlparse, urlunparse


class GitProvider(ABC):
    """Abstract base class for Git hosting providers."""

    def __init__(self, token: Optional[str] = None, base_url: Optional[str] = None):
        """
        Initialize the provider.

        Args:
            token: Authentication token for the provider
            base_url: Base URL for API calls (for self-hosted instances)
        """
        self.token = token
        self.base_url = base_url

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name for logging."""
        pass

    @property
    @abstractmethod
    def default_api_url(self) -> str:
        """Return the default API URL for this provider."""
        pass

    @abstractmethod
    def get_api_headers(self) -> Dict[str, str]:
        """
        Get HTTP headers for API requests including authentication.

        Returns:
            Dictionary of headers
        """
        pass

    @abstractmethod
    def validate_token(self) -> Dict:
        """
        Validate the authentication token.

        Returns:
            Dictionary with validation status and user info
        """
        pass

    @abstractmethod
    def get_user_info(self) -> Dict:
        """
        Get authenticated user information.

        Returns:
            Dictionary with user information
        """
        pass

    @abstractmethod
    def check_repository_permissions(self, repo_url: str) -> Dict:
        """
        Check permissions for a repository.

        Args:
            repo_url: Repository URL to check

        Returns:
            Dictionary with permission check results
        """
        pass

    @abstractmethod
    def list_organization_repos(self, org_name: str) -> List[Dict]:
        """
        List all repositories for an organization/group.

        Args:
            org_name: Organization or group name

        Returns:
            List of repository dictionaries
        """
        pass

    @abstractmethod
    def has_recent_activity(self, org_name: str, repo_name: str, years: int = 1) -> bool:
        """
        Check if repository has recent commits.

        Args:
            org_name: Organization or owner name
            repo_name: Repository name
            years: Number of years to look back

        Returns:
            True if repository has recent activity
        """
        pass

    @abstractmethod
    def get_auth_url(self, repo_url: str) -> str:
        """
        Add authentication to a repository URL for git operations.

        Args:
            repo_url: Original repository URL

        Returns:
            Repository URL with authentication added
        """
        pass

    def sanitize_url(self, url: str) -> str:
        """
        Remove sensitive information from URLs for safe logging.

        Args:
            url: URL that may contain authentication tokens

        Returns:
            Sanitized URL safe for logging
        """
        if not url or not url.startswith(('http://', 'https://')):
            return url

        parsed = urlparse(url)

        # Remove authentication info from the URL
        if parsed.username or parsed.password:
            sanitized_netloc = parsed.hostname or ''
            if parsed.port:
                sanitized_netloc += f":{parsed.port}"

            sanitized_url = urlunparse((
                parsed.scheme,
                sanitized_netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment
            ))
            return f"{sanitized_url} (authentication hidden)"

        # Check if token is embedded in the URL string
        if self.token and self.token in url:
            return url.replace(self.token, '***HIDDEN***')

        return url

    def _parse_repo_url(self, repo_url: str) -> tuple:
        """
        Parse a repository URL to extract owner and repo name.

        Args:
            repo_url: Repository URL

        Returns:
            Tuple of (owner, repo_name)
        """
        parsed = urlparse(repo_url)
        path = parsed.path.strip('/').rstrip('.git')
        parts = path.split('/')

        if len(parts) >= 2:
            # For GitLab, parts may include nested groups
            # Return the last part as repo and everything before as owner/path
            return '/'.join(parts[:-1]), parts[-1]

        return '', ''
