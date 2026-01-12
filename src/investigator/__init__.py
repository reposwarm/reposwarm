"""
OpenCode Investigator - AI-powered repository analysis.

This module provides the OpenCodeInvestigator class for analyzing repository
structure and generating architecture documentation using multiple AI providers.

Supported providers: Anthropic, OpenAI, Google, Bedrock, Azure, Ollama
"""

from .investigator import OpenCodeInvestigator, investigate_repo

# Backwards compatibility alias
ClaudeInvestigator = OpenCodeInvestigator

__all__ = [
    'OpenCodeInvestigator',
    'ClaudeInvestigator',  # Backwards compatibility
    'investigate_repo',
]
