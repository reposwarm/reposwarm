"""
Configuration constants for the Claude Investigator.
"""

import os


class Config:
    """Configuration constants for the investigator."""
    
    # Claude API settings - read from env, with sensible defaults
    CLAUDE_MODEL = os.getenv('ANTHROPIC_MODEL') or os.getenv('CLAUDE_MODEL') or "claude-sonnet-4-6-20260120"
    MAX_TOKENS = int(os.getenv('MAX_TOKENS', '6000'))

    # Input token limits — truncate prompts that would exceed the context window
    # 180K leaves room for output tokens within the 200K context window
    MAX_INPUT_TOKENS = int(os.getenv('MAX_INPUT_TOKENS', '180000'))
    CHARS_PER_TOKEN_ESTIMATE = float(os.getenv('CHARS_PER_TOKEN_ESTIMATE', '3.5'))

    # Valid Claude model names for validation (4.x models only)
    # See: https://platform.claude.com/docs/en/about-claude/models/overview
    VALID_CLAUDE_MODELS = [
        # Claude 4.6 (current)
        "claude-opus-4-6-20260120",
        "claude-sonnet-4-6-20260120",
        # Claude 4.5
        "claude-sonnet-4-5-20250929",
        "claude-haiku-4-5-20251001",
        "claude-opus-4-5-20251101",
        "claude-opus-4-1-20250805",
        # Claude 4.0 (legacy)
        "claude-sonnet-4-20250514",
        "claude-opus-4-20250514",
    ]
    
    # File settings
    ANALYSIS_FILE = "arch.md"
    
    # Logging format
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
    
    # Directory names
    TEMP_DIR = "temp"
    PROMPTS_DIR = "prompts"
    
    # Repository structure icons
    DIR_ICON = "📁"
    FILE_ICON = "📄"
    
    # Size units for human-readable format
    SIZE_UNITS = ['B', 'KB', 'MB', 'GB', 'TB']
    
    # Architecture Hub configuration
    # These values are read from environment variables with sensible defaults
    ARCH_HUB_REPO_NAME = os.getenv("ARCH_HUB_REPO_NAME", "architecture-hub")
    ARCH_HUB_BASE_URL = os.getenv("ARCH_HUB_BASE_URL", "https://github.com/your-org")
    ARCH_HUB_FILES_DIR = os.getenv("ARCH_HUB_FILES_DIR", "")  # Empty string means root directory
    
    # Repository scanning configuration
    # DEFAULT_ORG_NAME supports both GitHub organizations and individual user accounts
    DEFAULT_ORG_NAME = os.getenv("DEFAULT_ORG_NAME", "your-org")
    DEFAULT_REPO_URL = os.getenv("DEFAULT_REPO_URL", "https://github.com/facebook/react")
    
    # Git configuration for commits
    GIT_USER_NAME = os.getenv("GIT_USER_NAME", "Architecture Bot")
    GIT_USER_EMAIL = os.getenv("GIT_USER_EMAIL", "architecture-bot@your-org.com")
    
    @staticmethod
    def get_arch_hub_repo_url() -> str:
        """Get the full repository URL for the architecture hub.

        Smart URL construction:
        - If ARCH_HUB_BASE_URL looks like a full repo URL (3+ path segments), use it directly
        - If it looks like an org URL (2 path segments), append /{ARCH_HUB_REPO_NAME}
        """
        base_url = Config.ARCH_HUB_BASE_URL.rstrip('/')

        # Parse the URL to count path segments
        # Remove protocol if present
        url_without_protocol = base_url.split('://', 1)[-1]
        # Count path segments (everything after the host)
        path_parts = url_without_protocol.split('/', 1)
        if len(path_parts) > 1:
            path_segments = [p for p in path_parts[1].split('/') if p]
        else:
            path_segments = []

        # If 2+ path segments (e.g., github.com/org/repo), it's a full repo URL
        if len(path_segments) >= 2:
            # Use the base URL directly
            if not base_url.endswith('.git'):
                return f"{base_url}.git"
            return base_url
        else:
            # It's an org URL (e.g., github.com/org), append repo name
            return f"{base_url}/{Config.ARCH_HUB_REPO_NAME}.git"

    @staticmethod
    def get_arch_hub_web_url() -> str:
        """Get the web URL for the architecture hub (without .git extension).

        Smart URL construction:
        - If ARCH_HUB_BASE_URL looks like a full repo URL (3+ path segments), use it directly
        - If it looks like an org URL (2 path segments), append /{ARCH_HUB_REPO_NAME}
        """
        base_url = Config.ARCH_HUB_BASE_URL.rstrip('/')

        # Parse the URL to count path segments
        # Remove protocol if present
        url_without_protocol = base_url.split('://', 1)[-1]
        # Count path segments (everything after the host)
        path_parts = url_without_protocol.split('/', 1)
        if len(path_parts) > 1:
            path_segments = [p for p in path_parts[1].split('/') if p]
        else:
            path_segments = []

        # If 2+ path segments (e.g., github.com/org/repo), it's a full repo URL
        if len(path_segments) >= 2:
            # Use the base URL directly, remove .git if present
            return base_url.rstrip('.git').rstrip('/')
        else:
            # It's an org URL (e.g., github.com/org), append repo name
            return f"{base_url}/{Config.ARCH_HUB_REPO_NAME}"
    
    @staticmethod
    def get_default_org_github_url() -> str:
        """Get the GitHub URL for the default organization."""
        return f"https://github.com/{Config.DEFAULT_ORG_NAME}" 
    
    # Workflow configuration
    WORKFLOW_CHUNK_SIZE = 8  # Number of sub-workflows to run in parallel 
    WORKFLOW_SLEEP_HOURS = 6  # Hours to sleep between workflow executions
    
    @staticmethod
    def validate_claude_model(model_name: str) -> str:
        """Validate and return claude model name.
        
        Args:
            model_name: The model name to validate
            
        Returns:
            The validated model name
            
        Raises:
            ValueError: If model name is not in VALID_CLAUDE_MODELS
        """
        if model_name not in Config.VALID_CLAUDE_MODELS:
            # Allow Bedrock model IDs (e.g. us.anthropic.claude-sonnet-4-20250514-v1:0) to pass through
            if model_name.startswith(('us.anthropic.', 'anthropic.')):
                return model_name
            valid_models_str = ", ".join(Config.VALID_CLAUDE_MODELS)
            raise ValueError(f"Invalid Claude model '{model_name}'. Valid models: {valid_models_str}")
        return model_name
    
    @staticmethod
    def validate_max_tokens(tokens: int) -> int:
        """Validate and return max tokens value.
        
        Args:
            tokens: The max tokens value to validate
            
        Returns:
            The validated max tokens value
            
        Raises:
            ValueError: If tokens is not in valid range (100-100000)
        """
        if not isinstance(tokens, int) or tokens < 100 or tokens > 100000:
            raise ValueError(f"Invalid max_tokens '{tokens}'. Must be integer between 100 and 100000")
        return tokens
    
    @staticmethod
    def validate_sleep_hours(hours: float) -> float:
        """Validate and return sleep hours value.
        
        Args:
            hours: The sleep hours value to validate (supports fractional hours)
            
        Returns:
            The validated sleep hours value
            
        Raises:
            ValueError: If hours is not in valid range (0.01-168)
        """
        if not isinstance(hours, (int, float)) or hours < 0.01 or hours > 168:
            raise ValueError(f"Invalid sleep_hours '{hours}'. Must be number between 0.01 and 168 (36 seconds to 1 week)")
        return float(hours)
    
    @staticmethod
    def validate_chunk_size(size: int) -> int:
        """Validate and return chunk size value.
        
        Args:
            size: The chunk size value to validate
            
        Returns:
            The validated chunk size value
            
        Raises:
            ValueError: If size is not in valid range (1-20)
        """
        if not isinstance(size, int) or size < 1 or size > 20:
            raise ValueError(f"Invalid chunk_size '{size}'. Must be integer between 1 and 20")
        return size