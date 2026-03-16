"""
Claude API integration for the Claude Investigator.
"""

import os
from typing import Optional
from .config import Config


class ClaudeAnalyzer:
    """Handles Claude API interactions for analysis."""

    # Model mapping from standard Claude model names to Bedrock model IDs
    BEDROCK_MODEL_MAPPING = {
        "claude-opus-4-6-20260120": "us.anthropic.claude-opus-4-6",
        "claude-opus-4-5-20251101": "us.anthropic.claude-opus-4-5-20251101-v1:0",
        "claude-opus-4-1-20250805": "us.anthropic.claude-opus-4-1-20250805-v1:0",
        "claude-sonnet-4-6-20260120": "us.anthropic.claude-sonnet-4-6",
        "claude-sonnet-4-5-20250929": "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        "claude-sonnet-4-20250514": "us.anthropic.claude-sonnet-4-20250514-v1:0",
        "claude-haiku-4-5-20251001": "us.anthropic.claude-haiku-4-5-20251001-v1:0",
        "claude-opus-4-20250514": "us.anthropic.claude-opus-4-20250514-v1:0",
    }

    def __init__(self, api_key: str, logger):
        self.logger = logger
        self.use_bedrock = (
            os.getenv('CLAUDE_PROVIDER') == 'bedrock' or
            os.getenv('CLAUDE_CODE_USE_BEDROCK') == '1'
        )

        if self.use_bedrock:
            from anthropic import AnthropicBedrock
            aws_region = os.getenv('AWS_REGION', os.getenv('AWS_DEFAULT_REGION', 'us-east-1'))
            self.client = AnthropicBedrock(aws_region=aws_region)
            self.logger.info(f"Using Bedrock provider in region {aws_region}")
        else:
            from anthropic import Anthropic
            self.client = Anthropic(api_key=api_key)
            self.logger.info("Using standard Anthropic API")
    
    def _get_model_id(self, model_name: str) -> str:
        """
        Get the appropriate model ID for the current provider.

        For Bedrock, converts standard Claude model names to Bedrock model IDs.
        For standard API, returns the model name as-is.

        Args:
            model_name: Standard Claude model name

        Returns:
            Model ID appropriate for the current provider
        """
        if self.use_bedrock:
            bedrock_model = self.BEDROCK_MODEL_MAPPING.get(model_name)
            if bedrock_model:
                self.logger.debug(f"Mapped {model_name} to Bedrock model {bedrock_model}")
                return bedrock_model
            else:
                self.logger.info(f"No Bedrock mapping for {model_name}, using as-is")
                return model_name
        return model_name

    def clean_prompt(self, prompt_template: str) -> str:
        """
        Clean the prompt template by removing version lines and other metadata.
        
        Args:
            prompt_template: Raw prompt template that may contain version headers
            
        Returns:
            Cleaned prompt template ready for Claude
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
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count from character count using a conservative ratio."""
        if not text:
            return 0
        return int(len(text) / Config.CHARS_PER_TOKEN_ESTIMATE)

    def _truncate_to_fit(self, template: str, repo_structure: str,
                         previous_context: Optional[str]) -> tuple:
        """
        Truncate inputs if estimated token count exceeds MAX_INPUT_TOKENS.

        Truncation priority (most expendable first):
        1. repo_structure — usually the largest component, can be partially shown
        2. previous_context — helpful but not essential
        3. template — never truncated (this is the instruction)

        Returns:
            Tuple of (template, repo_structure, previous_context)
        """
        max_input = Config.MAX_INPUT_TOKENS
        template_tokens = self._estimate_tokens(template)
        structure_tokens = self._estimate_tokens(repo_structure)
        context_tokens = self._estimate_tokens(previous_context) if previous_context else 0
        total_tokens = template_tokens + structure_tokens + context_tokens

        if total_tokens <= max_input:
            return template, repo_structure, previous_context

        tokens_to_remove = total_tokens - max_input
        self.logger.warning(
            f"⚠️ Estimated {total_tokens:,} input tokens exceeds limit of {max_input:,}. "
            f"Template: {template_tokens:,}, Structure: {structure_tokens:,}, Context: {context_tokens:,}. "
            f"Need to remove ~{tokens_to_remove:,} tokens."
        )

        # Try truncating repo_structure first
        if structure_tokens > tokens_to_remove:
            max_chars = int((structure_tokens - tokens_to_remove) * Config.CHARS_PER_TOKEN_ESTIMATE)
            truncated = repo_structure[:max_chars]
            truncated += (
                f"\n\n... [TRUNCATED: showing first {max_chars:,} of "
                f"{len(repo_structure):,} characters to fit within {max_input:,} token limit] ..."
            )
            self.logger.warning(
                f"Truncated repo_structure from {len(repo_structure):,} to {len(truncated):,} chars"
            )
            return template, truncated, previous_context

        # Drop context if present
        if previous_context:
            self.logger.warning("Removing previous_context entirely to fit within token limit")
            previous_context = None
            tokens_to_remove -= context_tokens
            context_tokens = 0

            if tokens_to_remove <= 0:
                # Dropping context alone is sufficient
                return template, repo_structure, None

        # Truncate structure aggressively
        remaining_for_structure = max(max_input - template_tokens, 0)
        max_chars = int(remaining_for_structure * Config.CHARS_PER_TOKEN_ESTIMATE)
        max_chars = max(max_chars, 1000)  # Keep at least 1000 chars
        truncated = repo_structure[:max_chars]
        truncated += "\n\n... [TRUNCATED] ..."
        self.logger.warning(
            f"Truncated repo_structure from {len(repo_structure):,} to {len(truncated):,} chars"
            f"{' (also removed previous_context)' if context_tokens == 0 else ''}"
        )

        # If template alone still exceeds limit, truncate the template as a last resort
        if template_tokens > max_input:
            self.logger.warning(
                f"⚠️ Template alone ({template_tokens:,} tokens) exceeds limit ({max_input:,}). "
                f"Truncating template as last resort."
            )
            # Reserve tokens for structure placeholder and response overhead
            reserved_tokens = 2000
            max_template_chars = int((max_input - reserved_tokens) * Config.CHARS_PER_TOKEN_ESTIMATE)
            max_template_chars = max(max_template_chars, 10000)  # Keep at least 10K chars
            template = template[:max_template_chars]
            template += (
                f"\n\n... [TEMPLATE TRUNCATED: showing first {max_template_chars:,} of "
                f"{int(template_tokens * Config.CHARS_PER_TOKEN_ESTIMATE):,} characters "
                f"to fit within {max_input:,} token limit] ..."
            )
            self.logger.warning(
                f"Truncated template to {max_template_chars:,} chars"
            )

        return template, truncated, None

    def analyze_with_context(self, prompt_template: str, repo_structure: str,
                           previous_context: Optional[str] = None,
                           config_overrides: Optional[dict] = None) -> str:
        """
        Analyze using Claude with optional context from previous analyses.

        Args:
            prompt_template: Prompt template to use
            repo_structure: Repository structure string
            previous_context: Previous analysis results to include as context
            config_overrides: Optional dict with claude_model, max_tokens overrides

        Returns:
            Analysis result from Claude
        """
        if config_overrides is None:
            config_overrides = {}

        # Clean the prompt template first (remove version lines, etc.)
        cleaned_template = self.clean_prompt(prompt_template)

        # Validate and truncate if estimated tokens exceed the context window
        cleaned_template, repo_structure, previous_context = self._truncate_to_fit(
            cleaned_template, repo_structure, previous_context
        )

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
        
        try:
            # Use config overrides or defaults
            claude_model = config_overrides.get("claude_model") or Config.CLAUDE_MODEL
            max_tokens = config_overrides.get("max_tokens") or Config.MAX_TOKENS

            # Get the appropriate model ID for the current provider
            model_id = self._get_model_id(claude_model)

            self.logger.info("Sending analysis request to Claude API")
            self.logger.debug(f"Using model: {model_id}, max_tokens: {max_tokens}")

            response = self.client.messages.create(
                model=model_id,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )
            
            analysis_text = response.content[0].text
            self.logger.info(f"Received analysis from Claude ({len(analysis_text)} characters)")
            self.logger.debug(f"Analysis preview (first 1000 chars): {analysis_text[:1000]}...")
            
            return analysis_text
            
        except Exception as e:
            error_str = str(e)

            # Check for rate limit errors — sleep before re-raising so Temporal
            # retries after the rate limit window has passed
            try:
                from anthropic import RateLimitError
                if isinstance(e, RateLimitError):
                    retry_after = None
                    if hasattr(e, 'response') and e.response is not None:
                        retry_after = e.response.headers.get('retry-after')

                    if retry_after:
                        try:
                            wait_seconds = min(int(retry_after), 120)
                        except (ValueError, TypeError):
                            wait_seconds = 30
                    else:
                        wait_seconds = 30

                    self.logger.warning(
                        f"⚠️ Rate limited (429). Sleeping {wait_seconds}s before retry "
                        f"(retry-after: {retry_after})"
                    )
                    import time
                    time.sleep(wait_seconds)
                    self.logger.info(f"Rate limit backoff complete ({wait_seconds}s), re-raising for Temporal retry")
                    raise Exception(f"Rate limited by Claude API (slept {wait_seconds}s): {error_str}")
            except ImportError:
                pass  # anthropic not available, fall through to generic handling

            self.logger.error(f"Claude API request failed: {error_str}")
            raise Exception(f"Failed to get analysis from Claude: {error_str}")
    
    def analyze_structure(self, repo_structure: str, prompt_template: str) -> str:
        """
        Analyze repository structure using Claude.
        
        Args:
            repo_structure: Repository structure string
            prompt_template: Prompt template to use
            
        Returns:
            Analysis result from Claude
        """
        return self.analyze_with_context(prompt_template, repo_structure, None) 