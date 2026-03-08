"""
Unit tests for CodeCommit adapter in GitRepositoryManager.
Tests the CodeCommit URL detection, authentication, and repository listing functionality.
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
import sys

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src'))

from investigator.core.git_manager import GitRepositoryManager


class TestCodeCommitURLDetection:
    """Tests for CodeCommit URL detection."""

    def test_is_codecommit_url_detects_codecommit(self):
        """Test that CodeCommit URLs are correctly detected."""
        mock_logger = Mock()
        manager = GitRepositoryManager(mock_logger)

        url = "https://git-codecommit.us-east-1.amazonaws.com/v1/repos/test-repo"
        assert manager._is_codecommit_url(url) is True

    def test_is_codecommit_url_detects_different_regions(self):
        """Test that CodeCommit URLs from different regions are detected."""
        mock_logger = Mock()
        manager = GitRepositoryManager(mock_logger)

        urls = [
            "https://git-codecommit.us-west-2.amazonaws.com/v1/repos/test-repo",
            "https://git-codecommit.eu-west-1.amazonaws.com/v1/repos/test-repo",
            "https://git-codecommit.ap-southeast-1.amazonaws.com/v1/repos/test-repo",
        ]

        for url in urls:
            assert manager._is_codecommit_url(url) is True

    def test_is_codecommit_url_rejects_github(self):
        """Test that GitHub URLs are not detected as CodeCommit."""
        mock_logger = Mock()
        manager = GitRepositoryManager(mock_logger)

        url = "https://github.com/user/repo"
        assert manager._is_codecommit_url(url) is False

    def test_is_codecommit_url_rejects_other_aws_services(self):
        """Test that other AWS service URLs are not detected as CodeCommit."""
        mock_logger = Mock()
        manager = GitRepositoryManager(mock_logger)

        url = "https://s3.amazonaws.com/bucket/key"
        assert manager._is_codecommit_url(url) is False


class TestCodeCommitAuthentication:
    """Tests for CodeCommit authentication in _add_authentication."""

    def test_add_authentication_with_codecommit_credentials(self):
        """Test that CodeCommit credentials are added to CodeCommit URLs."""
        mock_logger = Mock()

        with patch.dict(os.environ, {
            'CODECOMMIT_USERNAME': 'test-user',
            'CODECOMMIT_PASSWORD': 'test-pass'
        }):
            manager = GitRepositoryManager(mock_logger)
            url = "https://git-codecommit.us-east-1.amazonaws.com/v1/repos/test-repo"

            auth_url = manager._add_authentication(url)

            assert auth_url == "https://test-user:test-pass@git-codecommit.us-east-1.amazonaws.com/v1/repos/test-repo"
            mock_logger.debug.assert_called_with("Added CodeCommit HTTPS authentication to repository URL")

    def test_add_authentication_without_codecommit_credentials(self):
        """Test that CodeCommit URLs without credentials are returned as-is with warning."""
        mock_logger = Mock()

        with patch.dict(os.environ, {}, clear=True):
            manager = GitRepositoryManager(mock_logger)
            url = "https://git-codecommit.us-east-1.amazonaws.com/v1/repos/test-repo"

            auth_url = manager._add_authentication(url)

            assert auth_url == url
            mock_logger.warning.assert_called_with("CodeCommit URL detected but credentials not available")

    def test_add_authentication_github_still_works(self):
        """Test that GitHub authentication still works when CodeCommit credentials are present."""
        mock_logger = Mock()

        with patch.dict(os.environ, {
            'GITHUB_TOKEN': 'github-token',
            'CODECOMMIT_USERNAME': 'cc-user',
            'CODECOMMIT_PASSWORD': 'cc-pass'
        }):
            manager = GitRepositoryManager(mock_logger)
            url = "https://github.com/user/repo"

            auth_url = manager._add_authentication(url)

            assert auth_url == "https://x-access-token:github-token@github.com/user/repo"
            mock_logger.debug.assert_called_with("Added GitHub token authentication to repository URL")

    def test_add_authentication_existing_auth_not_overridden(self):
        """Test that existing authentication in URL is not overridden."""
        mock_logger = Mock()

        with patch.dict(os.environ, {
            'CODECOMMIT_USERNAME': 'new-user',
            'CODECOMMIT_PASSWORD': 'new-pass'
        }):
            manager = GitRepositoryManager(mock_logger)
            url = "https://existing-user:existing-pass@git-codecommit.us-east-1.amazonaws.com/v1/repos/test-repo"

            auth_url = manager._add_authentication(url)

            assert auth_url == url
            mock_logger.debug.assert_called_with("Authentication already present in URL, not overriding")

    def test_add_authentication_non_http_urls_unchanged(self):
        """Test that non-HTTP URLs are not modified."""
        mock_logger = Mock()

        with patch.dict(os.environ, {
            'CODECOMMIT_USERNAME': 'test-user',
            'CODECOMMIT_PASSWORD': 'test-pass'
        }):
            manager = GitRepositoryManager(mock_logger)
            url = "/local/path/to/repo"

            auth_url = manager._add_authentication(url)

            assert auth_url == url


class TestCodeCommitPushAuthentication:
    """Tests for CodeCommit push authentication in push_with_authentication."""

    @patch('subprocess.run')
    def test_push_with_codecommit_credentials(self, mock_run):
        """Test that push updates remote URL with CodeCommit credentials."""
        mock_logger = Mock()

        with patch.dict(os.environ, {
            'CODECOMMIT_USERNAME': 'test-user',
            'CODECOMMIT_PASSWORD': 'test-pass'
        }):
            manager = GitRepositoryManager(mock_logger)

            # Mock get-url response
            get_url_result = Mock()
            get_url_result.returncode = 0
            get_url_result.stdout = "https://git-codecommit.us-east-1.amazonaws.com/v1/repos/test-repo\n"

            # Mock push response
            push_result = Mock()
            push_result.returncode = 0
            push_result.stdout = "Success"
            push_result.stderr = ""

            mock_run.side_effect = [get_url_result, Mock(), push_result]

            result = manager.push_with_authentication("/fake/repo", "main")

            assert result['status'] == 'success'
            # Verify remote URL was updated with credentials
            assert any(
                call[0][0] == ["git", "remote", "set-url", "origin",
                               "https://test-user:test-pass@git-codecommit.us-east-1.amazonaws.com/v1/repos/test-repo"]
                for call in mock_run.call_args_list
            )


class TestCodeCommitRepositoryListing:
    """Tests for CodeCommit repository listing via boto3."""

    @patch('boto3.client')
    def test_list_codecommit_repositories_success(self, mock_boto_client):
        """Test successful listing of CodeCommit repositories."""
        mock_logger = Mock()
        manager = GitRepositoryManager(mock_logger)

        # Mock CodeCommit client
        mock_cc_client = Mock()
        mock_boto_client.return_value = mock_cc_client

        # Mock list_repositories response
        mock_cc_client.list_repositories.return_value = {
            'repositories': [
                {'repositoryName': 'repo1'},
                {'repositoryName': 'repo2'}
            ]
        }

        # Mock get_repository responses
        def mock_get_repo(repositoryName):
            repos = {
                'repo1': {
                    'repositoryMetadata': {
                        'repositoryName': 'repo1',
                        'cloneUrlHttp': 'https://git-codecommit.us-east-1.amazonaws.com/v1/repos/repo1',
                        'cloneUrlSsh': 'ssh://git-codecommit.us-east-1.amazonaws.com/v1/repos/repo1',
                        'Arn': 'arn:aws:codecommit:us-east-1:123456789012:repo1',
                        'repositoryDescription': 'Test repo 1'
                    }
                },
                'repo2': {
                    'repositoryMetadata': {
                        'repositoryName': 'repo2',
                        'cloneUrlHttp': 'https://git-codecommit.us-east-1.amazonaws.com/v1/repos/repo2',
                        'cloneUrlSsh': 'ssh://git-codecommit.us-east-1.amazonaws.com/v1/repos/repo2',
                        'Arn': 'arn:aws:codecommit:us-east-1:123456789012:repo2',
                        'repositoryDescription': 'Test repo 2'
                    }
                }
            }
            return repos[repositoryName]

        mock_cc_client.get_repository.side_effect = mock_get_repo

        # Call the method
        result = manager.list_codecommit_repositories(region='us-east-1')

        # Verify results
        assert result['status'] == 'success'
        assert result['count'] == 2
        assert result['region'] == 'us-east-1'
        assert len(result['repositories']) == 2

        # Verify repository details
        repo1 = result['repositories'][0]
        assert repo1['name'] == 'repo1'
        assert repo1['clone_url_http'] == 'https://git-codecommit.us-east-1.amazonaws.com/v1/repos/repo1'
        assert repo1['description'] == 'Test repo 1'

    @patch('boto3.client')
    def test_list_codecommit_repositories_uses_default_region(self, mock_boto_client):
        """Test that default region is used when not specified."""
        mock_logger = Mock()
        manager = GitRepositoryManager(mock_logger)

        mock_cc_client = Mock()
        mock_boto_client.return_value = mock_cc_client
        mock_cc_client.list_repositories.return_value = {'repositories': []}

        with patch.dict(os.environ, {}, clear=True):
            result = manager.list_codecommit_repositories()

            assert result['region'] == 'us-east-1'
            mock_boto_client.assert_called_once_with('codecommit', region_name='us-east-1')

    @patch('boto3.client')
    def test_list_codecommit_repositories_uses_env_region(self, mock_boto_client):
        """Test that AWS_DEFAULT_REGION environment variable is used."""
        mock_logger = Mock()
        manager = GitRepositoryManager(mock_logger)

        mock_cc_client = Mock()
        mock_boto_client.return_value = mock_cc_client
        mock_cc_client.list_repositories.return_value = {'repositories': []}

        with patch.dict(os.environ, {'AWS_DEFAULT_REGION': 'us-west-2'}):
            result = manager.list_codecommit_repositories()

            assert result['region'] == 'us-west-2'
            mock_boto_client.assert_called_once_with('codecommit', region_name='us-west-2')

    @patch('boto3.client')
    def test_list_codecommit_repositories_handles_errors(self, mock_boto_client):
        """Test that errors during repository listing are handled gracefully."""
        mock_logger = Mock()
        manager = GitRepositoryManager(mock_logger)

        mock_cc_client = Mock()
        mock_boto_client.return_value = mock_cc_client
        mock_cc_client.list_repositories.side_effect = Exception("AWS API Error")

        result = manager.list_codecommit_repositories()

        assert result['status'] == 'error'
        assert 'AWS API Error' in result['error']
        mock_logger.error.assert_called()

    @patch('boto3.client')
    def test_list_codecommit_repositories_handles_get_repo_failure(self, mock_boto_client):
        """Test that failure to get details for individual repos is handled."""
        mock_logger = Mock()
        manager = GitRepositoryManager(mock_logger)

        mock_cc_client = Mock()
        mock_boto_client.return_value = mock_cc_client

        mock_cc_client.list_repositories.return_value = {
            'repositories': [
                {'repositoryName': 'repo1'}
            ]
        }

        mock_cc_client.get_repository.side_effect = Exception("Access denied")

        result = manager.list_codecommit_repositories()

        # Should still return success but with basic info
        assert result['status'] == 'success'
        assert result['count'] == 1
        repo = result['repositories'][0]
        assert repo['name'] == 'repo1'
        assert 'clone_url_http' in repo
        assert 'error' in repo
        mock_logger.warning.assert_called()

    @patch('boto3.client')
    def test_list_codecommit_repositories_returns_correct_structure(self, mock_boto_client):
        """Test that repository listing returns correct data structure."""
        mock_logger = Mock()
        manager = GitRepositoryManager(mock_logger)

        mock_cc_client = Mock()
        mock_boto_client.return_value = mock_cc_client

        mock_cc_client.list_repositories.return_value = {
            'repositories': [
                {'repositoryName': 'test-repo'}
            ]
        }

        mock_cc_client.get_repository.return_value = {
            'repositoryMetadata': {
                'repositoryName': 'test-repo',
                'cloneUrlHttp': 'https://git-codecommit.us-east-1.amazonaws.com/v1/repos/test-repo',
                'cloneUrlSsh': 'ssh://...',
                'Arn': 'arn:aws:...',
                'repositoryDescription': 'Test repository'
            }
        }

        result = manager.list_codecommit_repositories()

        # Verify result structure
        assert 'status' in result
        assert 'region' in result
        assert 'count' in result
        assert 'repositories' in result
        assert isinstance(result['repositories'], list)

        # Verify repository structure
        repo = result['repositories'][0]
        assert 'name' in repo
        assert 'clone_url_http' in repo
        assert 'description' in repo


class TestCodeCommitInitialization:
    """Tests for CodeCommit credentials initialization."""

    def test_git_manager_loads_codecommit_credentials(self):
        """Test that GitRepositoryManager loads CodeCommit credentials from environment."""
        mock_logger = Mock()

        with patch.dict(os.environ, {
            'CODECOMMIT_USERNAME': 'test-user',
            'CODECOMMIT_PASSWORD': 'test-pass'
        }):
            manager = GitRepositoryManager(mock_logger)

            assert manager.codecommit_username == 'test-user'
            assert manager.codecommit_password == 'test-pass'
            mock_logger.debug.assert_any_call("CodeCommit credentials found in environment")

    def test_git_manager_handles_missing_codecommit_credentials(self):
        """Test that GitRepositoryManager handles missing CodeCommit credentials."""
        mock_logger = Mock()

        with patch.dict(os.environ, {}, clear=True):
            manager = GitRepositoryManager(mock_logger)

            assert manager.codecommit_username is None
            assert manager.codecommit_password is None

    def test_git_manager_loads_both_github_and_codecommit(self):
        """Test that GitRepositoryManager can load both GitHub and CodeCommit credentials."""
        mock_logger = Mock()

        with patch.dict(os.environ, {
            'GITHUB_TOKEN': 'github-token',
            'CODECOMMIT_USERNAME': 'cc-user',
            'CODECOMMIT_PASSWORD': 'cc-pass'
        }):
            manager = GitRepositoryManager(mock_logger)

            assert manager.github_token == 'github-token'
            assert manager.codecommit_username == 'cc-user'
            assert manager.codecommit_password == 'cc-pass'
            assert any('GitHub token found' in str(call) for call in mock_logger.debug.call_args_list)
            assert any('CodeCommit credentials found' in str(call) for call in mock_logger.debug.call_args_list)
