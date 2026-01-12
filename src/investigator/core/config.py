"""
Configuration constants for the OpenCode Investigator.
"""

import os


class Config:
    """Configuration constants for the investigator."""

    # OpenCode server settings
    OPENCODE_PORT = int(os.getenv("OPENCODE_PORT", "4096"))

    # Provider configuration (configurable: anthropic, openai, google, bedrock, etc.)
    PROVIDER_ID = os.getenv("PROVIDER_ID", "anthropic")

    # Valid providers supported by OpenCode
    VALID_PROVIDERS = [
        "opencode",  # Free models provided by OpenCode
        "anthropic",
        "openai",
        "google",
        "bedrock",
        "azure",
        "ollama",
        "groq",
        "github-copilot",
    ]

    # Default model settings (configurable via environment)
    # If not set, uses provider-specific defaults
    MODEL_ID = os.getenv("MODEL_ID", "")  # e.g., "claude-opus-4-5-20251101", "gpt-4o", "gpt-5-nano"
    MAX_TOKENS = 6000

    # Provider-specific default models (used when MODEL_ID is not set)
    DEFAULT_MODELS = {
        "opencode": "gpt-5-nano",
        "anthropic": "claude-opus-4-5-20251101",
        "openai": "gpt-4o",
        "google": "gemini-2.0-flash",
        "groq": "llama-3.3-70b-versatile",
    }

    @staticmethod
    def get_default_model(provider_id: str) -> str:
        """Get the default model for a provider."""
        if Config.MODEL_ID:
            return Config.MODEL_ID
        return Config.DEFAULT_MODELS.get(provider_id, "claude-opus-4-5-20251101")

    # Valid model names per provider
    # Models are specified in format: provider/model-name
    VALID_MODELS = {
        "opencode": [
            # Free models provided by OpenCode
            "glm-4.7-free",
            "minimax-m2.1-free",
            "gpt-5-nano",
            "big-pickle",
            "grok-code",
        ],
        "anthropic": [
            "claude-sonnet-4-5-20250929",
            "claude-haiku-4-5-20251001",
            "claude-opus-4-5-20251101",  # current default
            "claude-opus-4-1-20250805",
            "claude-sonnet-4-20250514",
            "claude-opus-4-20250514",
        ],
        "openai": [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "o1-preview",
            "o1-mini",
        ],
        "google": [
            "gemini-2.0-flash",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
        ],
        "groq": [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
        ],
    }
    
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
        """Get the full repository URL for the architecture hub."""
        return f"{Config.ARCH_HUB_BASE_URL}/{Config.ARCH_HUB_REPO_NAME}.git"
    
    @staticmethod
    def get_arch_hub_web_url() -> str:
        """Get the web URL for the architecture hub (without .git extension)."""
        return f"{Config.ARCH_HUB_BASE_URL}/{Config.ARCH_HUB_REPO_NAME}"
    
    @staticmethod
    def get_default_org_github_url() -> str:
        """Get the GitHub URL for the default organization."""
        return f"https://github.com/{Config.DEFAULT_ORG_NAME}" 
    
    # Workflow configuration
    WORKFLOW_CHUNK_SIZE = 8  # Number of sub-workflows to run in parallel 
    WORKFLOW_SLEEP_HOURS = 6  # Hours to sleep between workflow executions
    
    @staticmethod
    def validate_provider(provider_id: str) -> str:
        """Validate and return provider ID.

        Args:
            provider_id: The provider ID to validate

        Returns:
            The validated provider ID

        Raises:
            ValueError: If provider_id is not in VALID_PROVIDERS
        """
        if provider_id not in Config.VALID_PROVIDERS:
            valid_providers_str = ", ".join(Config.VALID_PROVIDERS)
            raise ValueError(f"Invalid provider '{provider_id}'. Valid providers: {valid_providers_str}")
        return provider_id

    @staticmethod
    def validate_model(model_name: str, provider_id: str = None) -> str:
        """Validate and return model name for the given provider.

        Args:
            model_name: The model name to validate
            provider_id: The provider to validate against (optional, uses default if not provided)

        Returns:
            The validated model name

        Raises:
            ValueError: If model name is not valid for the provider
        """
        provider = provider_id or Config.PROVIDER_ID

        # If provider not in VALID_MODELS, allow any model (for flexibility with new providers)
        if provider not in Config.VALID_MODELS:
            return model_name

        if model_name not in Config.VALID_MODELS[provider]:
            valid_models_str = ", ".join(Config.VALID_MODELS[provider])
            raise ValueError(f"Invalid model '{model_name}' for provider '{provider}'. Valid models: {valid_models_str}")
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