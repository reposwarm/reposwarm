"""
Git repository management for the Claude Investigator.
"""

import os
import shutil
import subprocess
from typing import Optional
from urllib.parse import urlparse, urlunparse

from .providers import GitProvider, get_provider
from .utils import Utils


class GitRepositoryManager:
    """Handles Git repository operations."""

    def __init__(self, logger, provider: Optional[GitProvider] = None):
        """
        Initialize the Git repository manager.

        Args:
            logger: Logger instance
            provider: Optional GitProvider instance (auto-detected if not provided)
        """
        self.logger = logger
        self._provider = provider
        # Keep github_token for backward compatibility
        self.github_token = os.getenv('GITHUB_TOKEN')
        if self.github_token:
            self.logger.debug("GitHub token found in environment")

    @property
    def provider(self) -> GitProvider:
        """Lazy load provider based on environment configuration."""
        if self._provider is None:
            self._provider = get_provider()
            self.logger.debug(f"Using {self._provider.provider_name} provider")
        return self._provider

    def set_provider_from_url(self, repo_url: str):
        """
        Set provider based on repository URL.

        Args:
            repo_url: Repository URL to detect provider from
        """
        self._provider = get_provider(repo_url=repo_url)
        self.logger.debug(f"Using {self._provider.provider_name} provider for URL")
    
    def _sanitize_url_for_logging(self, url: str) -> str:
        """
        Remove sensitive information from URLs for safe logging.

        Args:
            url: URL that may contain authentication tokens or passwords

        Returns:
            Sanitized URL safe for logging
        """
        # Use provider's sanitize method if available
        return self.provider.sanitize_url(url)
    
    def clone_or_update(self, repo_location: str, target_dir: str) -> str:
        """
        Clone a repository or update it if it already exists.
        
        Args:
            repo_location: URL or path to the repository
            target_dir: Directory to clone/update the repository
            
        Returns:
            Path to the repository
        """
        # Add authentication to the URL if needed
        auth_repo_location = self._add_authentication(repo_location)
        
        if self._is_existing_repo(target_dir):
            return self._update_repository(target_dir, auth_repo_location)
        else:
            return self._clone_repository(auth_repo_location, target_dir)
    
    def _add_authentication(self, repo_location: str) -> str:
        """
        Add token authentication to repository URL if available.

        Uses the provider abstraction to handle GitHub/GitLab differences.

        Args:
            repo_location: Original repository URL

        Returns:
            Repository URL with authentication added if applicable
        """
        # Only process URLs, not local paths
        if not repo_location.startswith(('http://', 'https://')):
            return repo_location

        # Set provider based on URL for correct auth handling
        self.set_provider_from_url(repo_location)

        # Use provider to add authentication
        auth_url = self.provider.get_auth_url(repo_location)

        if auth_url != repo_location:
            self.logger.debug(f"Added {self.provider.provider_name} token authentication to repository URL")

        return auth_url
    
    def _is_existing_repo(self, repo_dir: str) -> bool:
        """Check if a directory contains a valid Git repository."""
        return os.path.exists(repo_dir) and os.path.exists(os.path.join(repo_dir, '.git'))
    
    def _update_repository(self, repo_dir: str, auth_repo_location: str) -> str:
        """Update an existing repository with latest changes."""
        self.logger.info(f"Repository already exists at: {repo_dir}")
        try:
            import git
            repo = git.Repo(repo_dir)
            self.logger.info("Pulling latest changes from remote repository")

            origin = repo.remotes.origin

            # Update remote URL with authentication if needed
            current_url = origin.url
            if '@' not in current_url and self.provider.token:
                self.logger.debug("Updating remote URL with authentication")
                origin.set_url(auth_repo_location)

            origin.fetch()
            origin.pull()

            self.logger.info(f"Repository successfully updated at: {repo_dir}")
            return repo_dir

        except Exception as e:
            # Import git to check for GitCommandError
            import git
            if isinstance(e, git.exc.GitCommandError):
                self.logger.warning(f"Failed to pull latest changes: {str(e)}")
                self.logger.info("Falling back to cloning the repository")
                shutil.rmtree(repo_dir)
                raise
            else:
                raise
    
    def _clone_repository(self, repo_location: str, target_dir: str) -> str:
        """Clone a new repository."""
        self._ensure_clean_directory(target_dir)

        try:
            import git
            # Log sanitized URL without exposing sensitive information
            safe_url = self._sanitize_url_for_logging(repo_location)
            self.logger.info(f"Cloning repository from: {safe_url}")

            if self.provider.token and self.provider.token in repo_location:
                self.logger.info(f"Using {self.provider.provider_name} token authentication for private repository access")

            git.Repo.clone_from(repo_location, target_dir)
            self.logger.info(f"Repository successfully cloned to: {target_dir}")
            return target_dir

        except Exception as e:
            import git
            if isinstance(e, git.exc.GitCommandError):
                self.logger.error(f"Git clone failed: {str(e)}")

                # Check if it's a resource issue (exit code -9 or similar)
                if "exit code(-9)" in str(e) or "Killed" in str(e):
                    self.logger.warning("Detected potential resource issue, attempting shallow clone")
                    # Clean up failed attempt
                    if os.path.exists(target_dir):
                        shutil.rmtree(target_dir, ignore_errors=True)

                    # Try shallow clone as fallback
                    try:
                        return self._shallow_clone_fallback(repo_location, target_dir)
                    except Exception as shallow_error:
                        self.logger.error(f"Shallow clone also failed: {str(shallow_error)}")
                        raise Exception(f"Failed to clone repository even with shallow clone: {str(shallow_error)}")

                # Don't include the full error message as it might contain the token
                if self.provider.token and "Authentication failed" in str(e):
                    raise Exception(f"Failed to clone repository: Authentication failed. Please check your {self.provider.provider_name.upper()}_TOKEN.")

                # Sanitize error message to remove any tokens
                error_msg = self._sanitize_error_message(str(e))
                raise Exception(f"Failed to clone repository: {error_msg}")
            else:
                raise

    def _sanitize_error_message(self, error_msg: str) -> str:
        """Remove any tokens from error messages."""
        if self.provider.token and self.provider.token in error_msg:
            error_msg = error_msg.replace(self.provider.token, '***HIDDEN***')
        # Also check legacy github_token for backward compatibility
        if self.github_token and self.github_token in error_msg:
            error_msg = error_msg.replace(self.github_token, '***HIDDEN***')
        return error_msg
    
    def _shallow_clone_fallback(self, repo_location: str, target_dir: str) -> str:
        """
        Perform a shallow clone as a fallback when normal clone fails due to resource constraints.

        Args:
            repo_location: Repository URL to clone (with authentication if needed)
            target_dir: Target directory for the clone

        Returns:
            Path to the cloned repository
        """
        self.logger.info("Attempting shallow clone with depth=1 to reduce memory usage")

        # Ensure target directory is clean
        self._ensure_clean_directory(target_dir)

        # Build git clone command with shallow options
        cmd = [
            'git', 'clone',
            '--depth', '1',
            '--single-branch',  # Only clone the default branch
            '--no-tags',  # Don't fetch tags to save space
            repo_location,
            target_dir
        ]

        # Log sanitized command
        safe_url = self._sanitize_url_for_logging(repo_location)
        log_cmd = f"git clone --depth 1 --single-branch --no-tags {safe_url} {target_dir}"
        self.logger.debug(f"Shallow clone command: {log_cmd}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
                check=True
            )

            self.logger.info(f"Repository successfully shallow cloned to: {target_dir}")
            return target_dir

        except subprocess.CalledProcessError as e:
            # Check if it's still a resource issue
            if e.returncode == -9 or "Killed" in e.stderr:
                self.logger.error("Even shallow clone was killed - severe resource constraints")
                # Try one more time with minimal clone
                return self._minimal_clone_fallback(repo_location, target_dir)

            # Clean up error message to not expose token
            error_msg = self._sanitize_error_message(e.stderr)
            raise Exception(f"Shallow clone failed: {error_msg}")
        except subprocess.TimeoutExpired:
            raise Exception("Shallow clone timed out after 10 minutes")
    
    def _minimal_clone_fallback(self, repo_location: str, target_dir: str) -> str:
        """
        Perform a minimal clone with the most aggressive optimizations for extremely constrained environments.

        Args:
            repo_location: Repository URL to clone (with authentication if needed)
            target_dir: Target directory for the clone

        Returns:
            Path to the cloned repository
        """
        self.logger.info("Attempting minimal clone with aggressive optimizations")

        # Ensure target directory exists
        os.makedirs(target_dir, exist_ok=True)

        try:
            # Initialize repository
            subprocess.run(['git', 'init'], cwd=target_dir, check=True)

            # Add remote (don't log the URL with potential token)
            safe_url = self._sanitize_url_for_logging(repo_location)
            self.logger.debug(f"Adding remote origin: {safe_url}")
            subprocess.run(['git', 'remote', 'add', 'origin', repo_location], cwd=target_dir, check=True)

            # Configure git to minimize memory usage
            subprocess.run(['git', 'config', 'core.compression', '0'], cwd=target_dir, check=True)
            subprocess.run(['git', 'config', 'http.postBuffer', '524288000'], cwd=target_dir, check=True)
            subprocess.run(['git', 'config', 'pack.windowMemory', '10m'], cwd=target_dir, check=True)
            subprocess.run(['git', 'config', 'pack.packSizeLimit', '100m'], cwd=target_dir, check=True)
            subprocess.run(['git', 'config', 'core.packedGitLimit', '128m'], cwd=target_dir, check=True)
            subprocess.run(['git', 'config', 'core.packedGitWindowSize', '128m'], cwd=target_dir, check=True)

            # Fetch with minimal data - using blob:none for lazy loading
            fetch_cmd = [
                'git', 'fetch',
                '--depth=1',
                '--no-tags',
                '--filter=blob:none',  # Lazy fetch blobs only when needed
                'origin', 'HEAD'
            ]

            result = subprocess.run(
                fetch_cmd,
                cwd=target_dir,
                capture_output=True,
                text=True,
                timeout=600,
                check=True
            )

            # Checkout the fetched branch
            subprocess.run(['git', 'checkout', 'FETCH_HEAD'], cwd=target_dir, check=True)

            self.logger.info(f"Repository successfully cloned with minimal strategy to: {target_dir}")
            return target_dir

        except subprocess.CalledProcessError as e:
            # Clean up error message to not expose token
            error_msg = self._sanitize_error_message(str(e))
            raise Exception(f"Minimal clone failed: {error_msg}")
        except subprocess.TimeoutExpired:
            raise Exception("Minimal clone timed out after 10 minutes")
    
    def push_with_authentication(self, repo_dir: str, branch: str = "main") -> dict:
        """
        Push changes to remote repository with proper authentication.

        Supports both GitHub and GitLab via provider abstraction.

        Args:
            repo_dir: Directory containing the git repository
            branch: Branch to push to (default: main)

        Returns:
            Dictionary with push result status and message
        """
        try:
            # Get current remote URL and set provider accordingly
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=repo_dir,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                current_url = result.stdout.strip()
                self.set_provider_from_url(current_url)

                # Log current remote URL (sanitized)
                safe_url = self._sanitize_url_for_logging(current_url)
                self.logger.info(f"Current remote URL: {safe_url}")

                # Add authentication if not already present
                if self.provider.token and '@' not in current_url:
                    if current_url.startswith('https://'):
                        auth_url = self.provider.get_auth_url(current_url)
                        self.logger.info(f"Updating remote URL with {self.provider.provider_name} token for push")
                        subprocess.run(
                            ["git", "remote", "set-url", "origin", auth_url],
                            cwd=repo_dir,
                            check=True
                        )
                else:
                    self.logger.info("Remote URL already has authentication")
            else:
                self.logger.warning("No provider token available - push may fail for private repositories")

            # Perform the push
            push_result = subprocess.run(
                ["git", "push", "origin", branch],
                cwd=repo_dir,
                capture_output=True,
                text=True
            )

            if push_result.returncode != 0:
                # Sanitize error message to avoid exposing tokens
                error_msg = self._sanitize_error_message(push_result.stderr)
                return {
                    "status": "failed",
                    "message": f"Failed to push changes: {error_msg}",
                    "stderr": error_msg
                }

            self.logger.info(f"Successfully pushed changes to {branch}")
            return {
                "status": "success",
                "message": f"Successfully pushed changes to {branch}",
                "stdout": push_result.stdout
            }

        except Exception as e:
            error_msg = self._sanitize_error_message(str(e))
            return {
                "status": "failed",
                "message": f"Push operation failed: {error_msg}",
                "error": error_msg
            }
    
    def validate_github_token(self) -> dict:
        """
        Validate the Git provider token and return user information.

        Note: Method name kept for backward compatibility, but now
        supports both GitHub and GitLab via provider abstraction.

        Returns:
            Dictionary with validation status and user info
        """
        return self.provider.validate_token()

    def validate_token(self) -> dict:
        """
        Validate the Git provider token and return user information.

        Returns:
            Dictionary with validation status and user info
        """
        return self.provider.validate_token()
    
    def configure_git_user(self, repo_dir: str, user_name: str, user_email: str) -> bool:
        """
        Configure git user for commits in the repository.
        
        Args:
            repo_dir: Directory containing the git repository
            user_name: Git user name
            user_email: Git user email
            
        Returns:
            True if configuration was successful, False otherwise
        """
        try:
            subprocess.run(
                ["git", "config", "user.name", user_name],
                cwd=repo_dir,
                check=True
            )
            subprocess.run(
                ["git", "config", "user.email", user_email],
                cwd=repo_dir,
                check=True
            )
            
            self.logger.info(f"Git configured with user: {user_name} <{user_email}>")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to configure git user: {str(e)}")
            return False
    
    def check_repository_permissions(self, repo_url: str) -> dict:
        """
        Check if the current token has push permissions to the repository.

        Supports both GitHub and GitLab via provider abstraction.

        Args:
            repo_url: Repository URL to check permissions for

        Returns:
            Dictionary with permission check results
        """
        # Set provider based on URL for correct permission checking
        self.set_provider_from_url(repo_url)
        return self.provider.check_repository_permissions(repo_url)
    
    def _ensure_clean_directory(self, directory: str):
        """Ensure a directory is clean and ready for use."""
        if os.path.exists(directory):
            self.logger.info(f"Cleaning up existing directory: {directory}")
            shutil.rmtree(directory)
        os.makedirs(directory, exist_ok=True) 