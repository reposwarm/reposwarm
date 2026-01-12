"""
Core components for the OpenCode Investigator.

This module supports multiple AI providers (Anthropic, OpenAI, Google, etc.)
through the OpenCode SDK.
"""

from .config import Config
from .utils import Utils
from .git_manager import GitRepositoryManager
from .repository_analyzer import RepositoryAnalyzer
from .file_manager import FileManager
from .repository_type_detector import RepositoryTypeDetector

# NOTE: OpenCodeAnalyzer and OpenCodeServerManager are intentionally excluded
# from __init__.py to avoid importing opencode_ai in workflow contexts
# (Temporal sandbox restriction). Import them directly when needed:
#   from .opencode_analyzer import OpenCodeAnalyzer
#   from .opencode_server import OpenCodeServerManager

__all__ = [
    'Config',
    'Utils',
    'GitRepositoryManager',
    'RepositoryAnalyzer',
    'FileManager',
    'RepositoryTypeDetector'
] 