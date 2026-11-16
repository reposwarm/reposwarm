"""
Claude API integration for the Claude Investigator.
"""

import os
from typing import Optional
from .config import Config


CONTEXT_PLACEHOLDER = "{previous_context}"

# The shared prompts end with this block. A missing context placeholder is
# put before it, so the context comes before the repository data.
REPO_STRUCTURE_SECTION = "\n---\n\n## Repository Structure and Files"


def ensure_context_placeholder(prompt_template: str, previous_context: Optional[str],
                               logger=None) -> str:
    """
    Make sure that a prompt template can receive the previous context.

    A step can declare "context" in prompts.json, but its prompt file can
    have no {previous_context} placeholder. Before this function, the context
    was then dropped with no message. If there is context and no placeholder,
    this function adds the placeholder before the repository structure
    section, or at the end of the template if that section is not found.

    Args:
        prompt_template: Prompt template (version line already removed)
        previous_context: Previous analysis results, or None
        logger: Optional logger for a warning

    Returns:
        The template, with a {previous_context} placeholder if it needs one
    """
    if not previous_context or not prompt_template or CONTEXT_PLACEHOLDER in prompt_template:
        return prompt_template

    if logger is not None:
        logger.warning(
            "Prompt has context but no {previous_context} placeholder; "
            "adding the context before the repository structure"
        )

    index = prompt_template.rfind(REPO_STRUCTURE_SECTION)
    if index == -1:
        return f"{prompt_template.rstrip()}\n\n{CONTEXT_PLACEHOLDER}\n"
    return f"{prompt_template[:index]}\n{CONTEXT_PLACEHOLDER}\n{prompt_template[index:]}"


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
    
    def ensure_context_placeholder(self, prompt_template: str,
                                   previous_context: Optional[str]) -> str:
        """Add a {previous_context} placeholder if the template needs one."""
        return ensure_context_placeholder(prompt_template, previous_context, self.logger)

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
        cleaned_template = self.ensure_context_placeholder(cleaned_template, previous_context)
        
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
            self.logger.error(f"Claude API request failed: {str(e)}")
            raise Exception(f"Failed to get analysis from Claude: {str(e)}")
    
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