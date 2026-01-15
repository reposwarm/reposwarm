"""
GitHub REST API v3 provider implementation.
"""

import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from urllib.parse import urlparse, urlunparse

import requests

from .base_provider import GitProvider


class GitHubProvider(GitProvider):
    """GitHub REST API v3 provider."""

    DEFAULT_API_URL = "https://api.github.com"

    def __init__(self, token: Optional[str] = None, base_url: Optional[str] = None):
        """
        Initialize the GitHub provider.

        Args:
            token: GitHub personal access token
            base_url: Base API URL (for GitHub Enterprise)
        """
        super().__init__(token, base_url or self.DEFAULT_API_URL)

    @property
    def provider_name(self) -> str:
        return "GitHub"

    @property
    def default_api_url(self) -> str:
        return self.DEFAULT_API_URL

    def get_api_headers(self) -> Dict[str, str]:
        """Get HTTP headers for GitHub API requests."""
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "RepoSwarm/1.0"
        }
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        return headers

    def validate_token(self) -> Dict:
        """Validate the GitHub token and return user information."""
        if not self.token:
            return {
                "status": "no_token",
                "message": "No GitHub token found"
            }

        try:
            response = requests.get(
                f"{self.base_url}/user",
                headers=self.get_api_headers(),
                timeout=10
            )

            if response.status_code == 200:
                user_info = response.json()
                return {
                    "status": "valid",
                    "message": f"GitHub token authenticated as user: {user_info.get('login', 'unknown')}",
                    "user": user_info.get('login', 'unknown'),
                    "user_info": user_info
                }
            else:
                return {
                    "status": "invalid",
                    "message": f"GitHub token validation failed: HTTP {response.status_code}",
                    "status_code": response.status_code
                }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Could not validate GitHub token: {str(e)}",
                "error": str(e)
            }

    def get_user_info(self) -> Dict:
        """Get authenticated user information."""
        result = self.validate_token()
        return result.get("user_info", {})

    def check_repository_permissions(self, repo_url: str) -> Dict:
        """Check if the token has push permissions to the repository."""
        if not self.token:
            return {
                "status": "no_token",
                "message": "No GitHub token available to check permissions"
            }

        try:
            # Parse GitHub URL to extract owner/repo
            owner, repo = self._parse_github_url(repo_url)
            if not owner or not repo:
                return {
                    "status": "invalid_url",
                    "message": "Could not parse repository owner/name from URL"
                }

            # Check repository permissions
            api_url = f"{self.base_url}/repos/{owner}/{repo}"
            response = requests.get(
                api_url,
                headers=self.get_api_headers(),
                timeout=10
            )

            if response.status_code == 200:
                repo_data = response.json()
                permissions = repo_data.get('permissions', {})

                can_push = permissions.get('push', False)
                can_admin = permissions.get('admin', False)

                if can_push or can_admin:
                    return {
                        "status": "allowed",
                        "message": f"Token has push permissions to {owner}/{repo}",
                        "permissions": permissions,
                        "owner": owner,
                        "repo": repo
                    }
                else:
                    return {
                        "status": "denied",
                        "message": f"Token does not have push permissions to {owner}/{repo}",
                        "permissions": permissions,
                        "owner": owner,
                        "repo": repo
                    }
            elif response.status_code == 404:
                return {
                    "status": "not_found",
                    "message": f"Repository {owner}/{repo} not found or no access",
                    "owner": owner,
                    "repo": repo
                }
            else:
                return {
                    "status": "error",
                    "message": f"GitHub API returned {response.status_code}",
                    "status_code": response.status_code,
                    "owner": owner,
                    "repo": repo
                }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to check repository permissions: {str(e)}",
                "error": str(e)
            }

    def list_organization_repos(self, org_name: str) -> List[Dict]:
        """Fetch all repositories from a GitHub organization or user."""
        # First, determine if this is a user or organization
        account_type = self._detect_account_type(org_name)

        if account_type == "user":
            base_url = f"{self.base_url}/users/{org_name}/repos"
        elif account_type == "organization":
            base_url = f"{self.base_url}/orgs/{org_name}/repos"
        else:
            return []

        repos = []
        page = 1
        per_page = 100

        while True:
            params = {
                "per_page": per_page,
                "page": page
            }

            try:
                response = requests.get(
                    base_url,
                    headers=self.get_api_headers(),
                    params=params
                )
                response.raise_for_status()

                page_repos = response.json()
                if not page_repos:
                    break

                repos.extend(page_repos)

                # Check rate limit
                if "X-RateLimit-Remaining" in response.headers:
                    remaining = int(response.headers["X-RateLimit-Remaining"])
                    if remaining < 10:
                        break

                page += 1
                time.sleep(0.2)  # Be nice to the API

            except requests.exceptions.RequestException:
                break

        return repos

    def has_recent_activity(self, org_name: str, repo_name: str, years: int = 1) -> bool:
        """Check if a repository has had commits in the past N years."""
        cutoff_date = datetime.now() - timedelta(days=365 * years)
        since_date = cutoff_date.isoformat() + "Z"

        url = f"{self.base_url}/repos/{org_name}/{repo_name}/commits"
        params = {
            "since": since_date,
            "per_page": 1
        }

        try:
            response = requests.get(
                url,
                headers=self.get_api_headers(),
                params=params
            )
            if response.status_code == 409:  # Empty repository
                return False
            if response.status_code == 404:  # Repository not found
                return False
            response.raise_for_status()

            commits = response.json()
            return len(commits) > 0

        except requests.exceptions.RequestException:
            # If we can't check, assume it's active
            return True

    def get_auth_url(self, repo_url: str) -> str:
        """Add GitHub token authentication to repository URL."""
        # Only process URLs, not local paths
        if not repo_url.startswith(('http://', 'https://')):
            return repo_url

        # Only add token for GitHub repositories
        if 'github.com' not in repo_url and self.base_url not in repo_url:
            return repo_url

        # If no token available, return original URL
        if not self.token:
            return repo_url

        # Parse the URL
        parsed = urlparse(repo_url)

        # If authentication already exists, don't override
        if parsed.username:
            return repo_url

        # Add token authentication (GitHub accepts token as username)
        auth_netloc = f"{self.token}@{parsed.hostname}"
        if parsed.port:
            auth_netloc += f":{parsed.port}"

        # Reconstruct the URL with authentication
        auth_url = urlunparse((
            parsed.scheme,
            auth_netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment
        ))

        return auth_url

    def _detect_account_type(self, account_name: str) -> str:
        """Detect whether the account is a user or organization."""
        try:
            response = requests.get(
                f"{self.base_url}/users/{account_name}",
                headers=self.get_api_headers()
            )

            if response.status_code == 200:
                account_data = response.json()
                account_type = account_data.get("type", "").lower()

                if account_type == "user":
                    return "user"
                elif account_type == "organization":
                    return "organization"

            return "unknown"

        except requests.exceptions.RequestException:
            return "unknown"

    def _parse_github_url(self, repo_url: str) -> tuple:
        """Parse GitHub URL to extract owner and repo name."""
        # Handle both https://github.com/owner/repo and https://github.com/owner/repo.git
        url_path = repo_url.replace('https://github.com/', '').replace('.git', '')

        # Handle GitHub Enterprise URLs
        if self.base_url != self.DEFAULT_API_URL:
            parsed = urlparse(repo_url)
            url_path = parsed.path.strip('/').rstrip('.git')

        if '/' not in url_path:
            return '', ''

        parts = url_path.split('/', 1)
        return parts[0], parts[1] if len(parts) > 1 else ''
