"""
GitLab REST API v4 provider implementation.
"""

import time
import urllib.parse
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from urllib.parse import urlparse, urlunparse

import requests

from .base_provider import GitProvider


class GitLabProvider(GitProvider):
    """GitLab REST API v4 provider."""

    DEFAULT_API_URL = "https://gitlab.com/api/v4"

    def __init__(self, token: Optional[str] = None, base_url: Optional[str] = None):
        """
        Initialize the GitLab provider.

        Args:
            token: GitLab personal access token
            base_url: Base URL for self-hosted GitLab instances
                      (e.g., "https://gitlab.mycompany.com")
        """
        # Handle base URL - ensure it has /api/v4 suffix
        if base_url:
            if not base_url.endswith("/api/v4"):
                base_url = base_url.rstrip("/") + "/api/v4"
            api_url = base_url
        else:
            api_url = self.DEFAULT_API_URL

        super().__init__(token, api_url)

        # Store web base URL (without /api/v4) for URL generation
        self.web_base_url = self.base_url.replace("/api/v4", "")

    @property
    def provider_name(self) -> str:
        return "GitLab"

    @property
    def default_api_url(self) -> str:
        return self.DEFAULT_API_URL

    def get_api_headers(self) -> Dict[str, str]:
        """Get HTTP headers for GitLab API requests."""
        headers = {
            "Accept": "application/json",
            "User-Agent": "RepoSwarm/1.0"
        }
        if self.token:
            # GitLab uses PRIVATE-TOKEN header (not Authorization: Bearer)
            headers["PRIVATE-TOKEN"] = self.token
        return headers

    def validate_token(self) -> Dict:
        """Validate the GitLab token and return user information."""
        if not self.token:
            return {
                "status": "no_token",
                "message": "No GitLab token found"
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
                    "message": f"GitLab token authenticated as user: {user_info.get('username', 'unknown')}",
                    "user": user_info.get('username', 'unknown'),
                    "user_info": user_info
                }
            elif response.status_code == 401:
                return {
                    "status": "invalid",
                    "message": "GitLab token is invalid or expired",
                    "status_code": response.status_code
                }
            else:
                return {
                    "status": "invalid",
                    "message": f"GitLab token validation failed: HTTP {response.status_code}",
                    "status_code": response.status_code
                }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Could not validate GitLab token: {str(e)}",
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
                "message": "No GitLab token available to check permissions"
            }

        try:
            # Extract and encode project path
            project_path = self._extract_project_path(repo_url)
            if not project_path:
                return {
                    "status": "invalid_url",
                    "message": "Could not parse project path from URL"
                }

            encoded_path = urllib.parse.quote(project_path, safe='')
            api_url = f"{self.base_url}/projects/{encoded_path}"

            response = requests.get(
                api_url,
                headers=self.get_api_headers(),
                timeout=10
            )

            if response.status_code == 200:
                project = response.json()
                permissions = project.get('permissions', {})

                # GitLab access levels:
                # 0 = No access, 10 = Guest, 20 = Reporter,
                # 30 = Developer, 40 = Maintainer, 50 = Owner
                project_access = permissions.get('project_access', {}) or {}
                group_access = permissions.get('group_access', {}) or {}

                access_level = max(
                    project_access.get('access_level', 0) or 0,
                    group_access.get('access_level', 0) or 0
                )

                # Developer (30) and above can push
                can_push = access_level >= 30

                if can_push:
                    return {
                        "status": "allowed",
                        "message": f"Token has push permissions to {project_path}",
                        "permissions": permissions,
                        "access_level": access_level,
                        "project_path": project_path
                    }
                else:
                    return {
                        "status": "denied",
                        "message": f"Token does not have push permissions to {project_path}",
                        "permissions": permissions,
                        "access_level": access_level,
                        "project_path": project_path
                    }
            elif response.status_code == 404:
                return {
                    "status": "not_found",
                    "message": f"Project {project_path} not found or no access",
                    "project_path": project_path
                }
            else:
                return {
                    "status": "error",
                    "message": f"GitLab API returned {response.status_code}",
                    "status_code": response.status_code,
                    "project_path": project_path
                }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to check repository permissions: {str(e)}",
                "error": str(e)
            }

    def list_organization_repos(self, org_name: str) -> List[Dict]:
        """Fetch all repositories from a GitLab group or user."""
        # First, try to fetch as a group
        encoded_name = urllib.parse.quote(org_name, safe='')

        # Check if it's a group
        group_url = f"{self.base_url}/groups/{encoded_name}"
        try:
            group_response = requests.get(
                group_url,
                headers=self.get_api_headers()
            )

            if group_response.status_code == 200:
                # It's a group - get group projects
                url = f"{self.base_url}/groups/{encoded_name}/projects"
                params = {"include_subgroups": "true"}
            else:
                # Try as user
                url = f"{self.base_url}/users/{org_name}/projects"
                params = {}

        except requests.exceptions.RequestException:
            url = f"{self.base_url}/users/{org_name}/projects"
            params = {}

        repos = []
        page = 1
        per_page = 100

        while True:
            request_params = {
                "per_page": per_page,
                "page": page,
                **params
            }

            try:
                response = requests.get(
                    url,
                    headers=self.get_api_headers(),
                    params=request_params
                )
                response.raise_for_status()

                page_repos = response.json()
                if not page_repos:
                    break

                # Normalize GitLab response to match expected format
                for repo in page_repos:
                    # Add 'name' field if only 'path' exists
                    if 'name' not in repo and 'path' in repo:
                        repo['name'] = repo['path']
                    # Add 'html_url' if only 'web_url' exists
                    if 'html_url' not in repo and 'web_url' in repo:
                        repo['html_url'] = repo['web_url']

                repos.extend(page_repos)
                page += 1
                time.sleep(0.2)

            except requests.exceptions.RequestException:
                break

        return repos

    def has_recent_activity(self, org_name: str, repo_name: str, years: int = 1) -> bool:
        """Check if a repository has had commits in the past N years."""
        project_path = f"{org_name}/{repo_name}"
        encoded_path = urllib.parse.quote(project_path, safe='')

        cutoff_date = datetime.now() - timedelta(days=365 * years)

        url = f"{self.base_url}/projects/{encoded_path}/repository/commits"
        params = {
            "since": cutoff_date.isoformat(),
            "per_page": 1
        }

        try:
            response = requests.get(
                url,
                headers=self.get_api_headers(),
                params=params
            )

            if response.status_code == 404:
                return False
            response.raise_for_status()

            commits = response.json()
            return len(commits) > 0

        except requests.exceptions.RequestException:
            # If we can't check, assume it's active
            return True

    def get_auth_url(self, repo_url: str) -> str:
        """Add GitLab token authentication to repository URL."""
        # Only process URLs, not local paths
        if not repo_url.startswith(('http://', 'https://')):
            return repo_url

        # If no token available, return original URL
        if not self.token:
            return repo_url

        # Parse the URL
        parsed = urlparse(repo_url)

        # If authentication already exists, don't override
        if parsed.username:
            return repo_url

        # GitLab uses oauth2:TOKEN format for HTTPS authentication
        auth_netloc = f"oauth2:{self.token}@{parsed.hostname}"
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

    def _extract_project_path(self, repo_url: str) -> str:
        """
        Extract GitLab project path from URL.

        GitLab URLs can have nested groups:
        https://gitlab.com/group/subgroup/project

        Args:
            repo_url: Repository URL

        Returns:
            Project path (e.g., "group/subgroup/project")
        """
        parsed = urlparse(repo_url)
        path = parsed.path.strip('/').rstrip('/')

        # Remove .git suffix if present
        if path.endswith('.git'):
            path = path[:-4]

        return path

    def _is_gitlab_url(self, url: str) -> bool:
        """Check if a URL is a GitLab URL."""
        parsed = urlparse(url)
        hostname = parsed.hostname or ""

        # Check for gitlab.com or self-hosted instance
        if "gitlab" in hostname.lower():
            return True

        # Check if it matches our configured base URL
        if self.web_base_url and self.web_base_url in url:
            return True

        return False
