"""
OpenCode API integration for the repository investigator.

This module replaces claude_analyzer.py and uses the OpenCode CLI
for multi-provider AI model access.
"""

import subprocess
import json
import tempfile
import os
from typing import Optional
from .config import Config


class OpenCodeAnalyzer:
    """Handles OpenCode API interactions for analysis."""

    def __init__(self, base_url: str, provider_id: str, logger):
        """
        Initialize the analyzer.

        Args:
            base_url: Base URL for the OpenCode server
            provider_id: Provider ID (e.g., "anthropic", "openai", "google", "opencode")
            logger: Logger instance
        """
        self.base_url = base_url
        self.provider_id = provider_id
        self.logger = logger

    def clean_prompt(self, prompt_template: str) -> str:
        """
        Clean the prompt template by removing version lines and other metadata.

        Args:
            prompt_template: Raw prompt template that may contain version headers

        Returns:
            Cleaned prompt template ready for the AI model
        """
        if not prompt_template:
            return prompt_template

        lines = prompt_template.split('\n')

        # Only clean if version line exists at the beginning
        if lines and lines[0].startswith('version'):
            lines = lines[1:]
            self.logger.debug("Removed version line from prompt")

            # Remove any leading empty lines after version removal
            while lines and lines[0].strip() == '':
                lines = lines[1:]

            cleaned_prompt = '\n'.join(lines)
            self.logger.debug(f"Cleaned prompt ({len(cleaned_prompt)} characters)")

            return cleaned_prompt
        else:
            # No version line found, return as-is
            return prompt_template

    def analyze_with_context(
        self,
        prompt_template: str,
        repo_structure: str,
        previous_context: Optional[str] = None,
        config_overrides: Optional[dict] = None
    ) -> str:
        """
        Analyze using OpenCode with optional context from previous analyses.

        Args:
            prompt_template: Prompt template to use
            repo_structure: Repository structure string
            previous_context: Previous analysis results to include as context
            config_overrides: Optional dict with model_id, max_tokens, provider_id overrides

        Returns:
            Analysis result from the AI model
        """
        if config_overrides is None:
            config_overrides = {}

        # Clean the prompt template first (remove version lines, etc.)
        cleaned_template = self.clean_prompt(prompt_template)

        # Replace placeholders in the cleaned prompt
        prompt = cleaned_template.replace("{repo_structure}", repo_structure)

        # Add previous context if available
        if previous_context:
            context_section = f"\n\n## Previous Analysis Context\n\n{previous_context}\n\n"
            prompt = prompt.replace("{previous_context}", context_section)
        else:
            # Remove the placeholder if no context
            prompt = prompt.replace("{previous_context}", "")

        self.logger.debug(f"Prompt created ({len(prompt)} characters)")
        self.logger.debug(f"Prompt preview (first 1000 chars): {prompt[:1000]}...")

        # Get config values
        provider_id = config_overrides.get("provider_id") or self.provider_id

        # Get model_id - use provider-specific default if using opencode provider
        model_id = config_overrides.get("model_id") or config_overrides.get("claude_model")
        if not model_id:
            if provider_id == "opencode":
                # Use free model for opencode provider
                model_id = "gpt-5-nano"
            else:
                model_id = Config.DEFAULT_MODEL

        # Format model as provider/model
        full_model = f"{provider_id}/{model_id}"

        self.logger.info("Sending analysis request to OpenCode")
        self.logger.debug(f"Using model: {full_model}")

        try:
            # Use opencode CLI with --attach to connect to the running server
            # Pass the prompt directly as the message argument
            cmd = [
                "opencode", "run",
                "--attach", self.base_url,
                "--model", full_model,
                "--format", "json",
                prompt  # The prompt is passed as the message
            ]

            self.logger.debug(f"Running opencode command with {len(prompt)} char prompt")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )

            if result.returncode != 0:
                self.logger.error(f"OpenCode CLI failed: {result.stderr}")
                raise Exception(f"OpenCode CLI failed: {result.stderr}")

            # Parse JSON output to extract text
            analysis_text = self._extract_text_from_json_output(result.stdout)

            self.logger.info(f"Received analysis from OpenCode ({len(analysis_text)} characters)")
            self.logger.debug(f"Analysis preview (first 1000 chars): {analysis_text[:1000]}...")

            return analysis_text

        except subprocess.TimeoutExpired:
            self.logger.error("OpenCode request timed out after 10 minutes")
            raise Exception("OpenCode request timed out")

        except Exception as e:
            self.logger.error(f"OpenCode request failed: {str(e)}")
            raise Exception(f"Failed to get analysis from OpenCode: {str(e)}")

    def _extract_text_from_json_output(self, output: str) -> str:
        """
        Extract text content from OpenCode JSON output.

        Args:
            output: Raw JSON output from opencode run --format json

        Returns:
            Extracted text content
        """
        text_parts = []

        # Parse each line as a separate JSON object
        for line in output.strip().split('\n'):
            if not line.strip():
                continue

            try:
                event = json.loads(line)

                # Extract text from "text" type events
                if event.get("type") == "text":
                    part = event.get("part", {})
                    if part.get("text"):
                        text_parts.append(part["text"])

                # Check for errors
                if event.get("type") == "error":
                    error_data = event.get("error", {})
                    error_msg = error_data.get("data", {}).get("message", str(error_data))
                    raise Exception(f"OpenCode error: {error_msg}")

            except json.JSONDecodeError:
                # Skip non-JSON lines
                continue

        return "".join(text_parts)

    def analyze_structure(self, repo_structure: str, prompt_template: str) -> str:
        """
        Analyze repository structure using OpenCode.

        Args:
            repo_structure: Repository structure string
            prompt_template: Prompt template to use

        Returns:
            Analysis result from the AI model
        """
        return self.analyze_with_context(prompt_template, repo_structure, None)


# Backwards compatibility alias
ClaudeAnalyzer = OpenCodeAnalyzer
