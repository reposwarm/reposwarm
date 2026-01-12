"""
Unit tests for OpenCodeAnalyzer prompt cleaning functionality.

These tests verify that version lines and metadata are properly removed
from prompts before sending to the AI model.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
import json

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from investigator.core.opencode_analyzer import OpenCodeAnalyzer

# Backwards compatibility alias for test naming
ClaudeAnalyzer = OpenCodeAnalyzer


class TestClaudeAnalyzerPromptCleaning(unittest.TestCase):
    """Test suite for prompt cleaning functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_logger = Mock()
        # No SDK mocking needed - OpenCodeAnalyzer uses subprocess CLI calls
        self.analyzer = OpenCodeAnalyzer("http://localhost:4096", "anthropic", self.mock_logger)

    def test_clean_prompt_removes_version_line(self):
        """Test that version lines are removed from prompts."""
        prompt_with_version = """version=2
## Repository Structure and Files

{repo_structure}
---

Act as a senior software architect..."""

        cleaned = self.analyzer.clean_prompt(prompt_with_version)

        # Should not contain version line
        self.assertNotIn("version=2", cleaned)

        # Should start with the actual content
        self.assertTrue(cleaned.startswith("## Repository Structure"))

        # Should log the removal
        self.mock_logger.debug.assert_called()
        debug_calls = [str(call) for call in self.mock_logger.debug.call_args_list]
        self.assertTrue(any("Removed version line" in call for call in debug_calls))

    def test_clean_prompt_handles_no_version_line(self):
        """Test that prompts without version lines are unchanged."""
        prompt_without_version = """## Repository Structure and Files

{repo_structure}
---

Act as a senior software architect..."""

        cleaned = self.analyzer.clean_prompt(prompt_without_version)

        # Should be exactly the same - no cleaning needed
        self.assertEqual(cleaned, prompt_without_version)

        # Should not log any cleaning activity
        debug_calls = [str(call) for call in self.mock_logger.debug.call_args_list]
        self.assertFalse(any("Removed version line" in call for call in debug_calls))
        self.assertFalse(any("Cleaned prompt" in call for call in debug_calls))

    def test_clean_prompt_removes_empty_lines_after_version(self):
        """Test that empty lines after version removal are cleaned up."""
        prompt_with_version_and_empty_lines = """version=1


## Repository Structure and Files

{repo_structure}"""

        cleaned = self.analyzer.clean_prompt(prompt_with_version_and_empty_lines)

        # Should start directly with content, no empty lines
        self.assertTrue(cleaned.startswith("## Repository Structure"))

        # Should not have leading newlines
        self.assertFalse(cleaned.startswith('\n'))

    def test_clean_prompt_handles_empty_input(self):
        """Test that empty or None input is handled gracefully."""
        self.assertEqual(self.analyzer.clean_prompt(""), "")
        self.assertEqual(self.analyzer.clean_prompt(None), None)

    def test_clean_prompt_handles_only_version_line(self):
        """Test handling of prompts that only contain a version line."""
        prompt_only_version = "version=3"

        cleaned = self.analyzer.clean_prompt(prompt_only_version)

        # Should result in empty string
        self.assertEqual(cleaned, "")

    def test_clean_prompt_preserves_version_in_content(self):
        """Test that version references within content are preserved."""
        prompt_with_content_version = """version=1
This is a prompt about version control.
We use version=2.0 of our API.
The version field should be removed from the top only."""

        cleaned = self.analyzer.clean_prompt(prompt_with_content_version)

        # Should not start with version=1
        self.assertNotIn("version=1", cleaned)

        # Should preserve version references in content
        self.assertIn("version=2.0", cleaned)
        self.assertIn("version field", cleaned)

    @patch('investigator.core.opencode_analyzer.subprocess.run')
    def test_analyze_with_context_uses_cleaned_prompt(self, mock_run):
        """Test that analyze_with_context uses cleaned prompts."""
        # Setup mock subprocess result with JSON output
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({"type": "text", "part": {"text": "Analysis result"}})
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        # Create analyzer
        analyzer = OpenCodeAnalyzer("http://localhost:4096", "anthropic", self.mock_logger)

        # Test with versioned prompt
        versioned_prompt = """version=2
Analyze this repository: {repo_structure}"""

        result = analyzer.analyze_with_context(
            versioned_prompt,
            "repo structure here"
        )

        # Verify result
        self.assertEqual(result, "Analysis result")

        # Verify subprocess was called
        mock_run.assert_called_once()
        call_args = mock_run.call_args

        # The command should be in the first positional argument
        cmd = call_args[0][0]

        # Find the prompt in the command (it's the last argument)
        sent_prompt = cmd[-1]

        # Version line should be removed
        self.assertNotIn("version=2", sent_prompt)

        # But the content should be there
        self.assertIn("Analyze this repository:", sent_prompt)
        self.assertIn("repo structure here", sent_prompt)

    def test_clean_prompt_logs_cleaning_info(self):
        """Test that prompt cleaning logs appropriate debug information."""
        prompt = """version=3
Some content here"""

        self.analyzer.clean_prompt(prompt)

        # Should log both version removal and final size
        debug_calls = [str(call) for call in self.mock_logger.debug.call_args_list]

        self.assertTrue(any("Removed version line" in call for call in debug_calls))
        self.assertTrue(any("Cleaned prompt" in call for call in debug_calls))


if __name__ == "__main__":
    unittest.main()
