"""
Storage key generation utilities for consistent naming across storage providers.

This module provides a centralized way to generate storage keys that work
consistently across both DynamoDB and file-based storage systems.
"""

import re
from typing import Optional, Tuple
from pydantic import BaseModel, Field, validator


def _sanitize_for_filesystem(name: str) -> str:
    """Sanitize a string for use as a filesystem path component.
    
    Handles URLs (https://github.com/org/repo), paths, and special chars.
    """
    # Strip common URL prefixes
    for prefix in ('https://', 'http://', 'git@', 'ssh://'):
        if name.startswith(prefix):
            name = name[len(prefix):]
            break
    # Replace path separators, colons, and other unsafe chars with underscores
    name = re.sub(r'[/\\:*?"<>|@#]', '_', name)
    # Collapse multiple underscores
    name = re.sub(r'_+', '_', name)
    # Strip leading/trailing underscores and dots
    name = name.strip('_.')
    return name


class PromptCacheKey(BaseModel):
    """Model for generating prompt cache keys."""
    repo_name: str = Field(..., description="Repository name")
    step_name: str = Field(..., description="Analysis step/prompt name")
    commit_sha: str = Field(..., description="Git commit SHA")
    prompt_version: str = Field(default="1", description="Prompt version")
    
    @validator('repo_name', 'step_name')
    def validate_no_special_chars(cls, v):
        """Sanitize names for safe use in file names and storage keys."""
        # Sanitize URLs and special chars instead of rejecting them
        return _sanitize_for_filesystem(v)
    
    @validator('commit_sha')
    def validate_commit_sha(cls, v):
        """Ensure commit SHA is valid."""
        if not v or len(v) < 6:  # Allow shorter SHAs for testing (min 6 chars)
            raise ValueError(f"Invalid commit SHA: {v}")
        return v
    
    def to_storage_key(self) -> str:
        """Generate the storage key for this prompt cache entry."""
        return f"{self.repo_name}_{self.step_name}_{self.commit_sha}_v{self.prompt_version}"
    
    def to_file_safe_key(self) -> str:
        """Generate a file-system safe version of the key."""
        safe_repo = _sanitize_for_filesystem(self.repo_name)
        return f"{safe_repo}_{self.step_name}_{self.commit_sha}_v{self.prompt_version}"
    
    @classmethod
    def parse_from_key(cls, storage_key: str) -> Optional['PromptCacheKey']:
        """
        Parse a storage key back into a PromptCacheKey object.
        
        Args:
            storage_key: The storage key string to parse
            
        Returns:
            PromptCacheKey object or None if parsing fails
        """
        try:
            # Split by underscore, but need to handle the version part specially
            # Format: repo_step_commit_vVersion
            parts = storage_key.rsplit('_v', 1)  # Split from right to get version
            if len(parts) == 2:
                main_parts = parts[0].rsplit('_', 2)  # Split the rest
                if len(main_parts) == 3:
                    return cls(
                        repo_name=main_parts[0],
                        step_name=main_parts[1],
                        commit_sha=main_parts[2],
                        prompt_version=parts[1]
                    )
        except Exception:
            pass
        return None


class AnalysisResultKey(BaseModel):
    """Model for generating analysis result keys."""
    reference_key: str = Field(..., description="Unique reference key for the result")
    
    def to_storage_key(self) -> str:
        """Generate the storage key for DynamoDB."""
        return f"_result_{self.reference_key}"
    
    def to_file_safe_key(self) -> str:
        """Generate a file-system safe version of the key - SAME as storage key."""
        # Use the exact same format as storage key
        return self.to_storage_key()
    
    @classmethod
    def parse_from_key(cls, storage_key: str) -> Optional['AnalysisResultKey']:
        """
        Parse a storage key back into an AnalysisResultKey object.
        
        Args:
            storage_key: The storage key string to parse
            
        Returns:
            AnalysisResultKey object or None if parsing fails
        """
        try:
            if storage_key.startswith('_result_'):
                return cls(reference_key=storage_key[8:])  # Remove '_result_' prefix
        except Exception:
            pass
        return None


class InvestigationMetadataKey(BaseModel):
    """Model for generating investigation metadata keys."""
    repo_name: str = Field(..., description="Repository name")
    analysis_type: str = Field(default="investigation", description="Type of analysis")
    
    @validator('repo_name')
    def validate_repo_name(cls, v):
        """Ensure repo name is valid."""
        if not v:
            raise ValueError("Repository name cannot be empty")
        return v
    
    def to_storage_key(self) -> str:
        """Generate the storage key for investigation metadata."""
        # Just the repo name for DynamoDB partition key
        return self.repo_name
    
    def to_file_safe_key(self) -> str:
        """Generate a file-system safe version of the key."""
        safe_repo = _sanitize_for_filesystem(self.repo_name)
        return f"{safe_repo}_{self.analysis_type}"
    
    @classmethod
    def parse_from_key(cls, storage_key: str) -> Optional['InvestigationMetadataKey']:
        """
        Parse a storage key back into an InvestigationMetadataKey object.
        
        Args:
            storage_key: The storage key string to parse
            
        Returns:
            InvestigationMetadataKey object or None if parsing fails
        """
        try:
            # Try to parse as file key format first (repo_type)
            if '_' in storage_key:
                parts = storage_key.rsplit('_', 1)
                if len(parts) == 2:
                    return cls(repo_name=parts[0], analysis_type=parts[1])
            # Otherwise assume it's just a repo name
            return cls(repo_name=storage_key, analysis_type="investigation")
        except Exception:
            pass
        return None


class PromptDataKey(BaseModel):
    """Model for generating prompt data storage keys."""
    repo_name: str = Field(..., description="Repository name")
    step_name: str = Field(..., description="Analysis step name")
    unique_id: str = Field(..., description="Unique identifier for this prompt data")
    
    def to_storage_key(self) -> str:
        """Generate the storage key for prompt data."""
        return f"{self.repo_name}_{self.step_name}_{self.unique_id}"
    
    def to_file_safe_key(self) -> str:
        """Generate a file-system safe version of the key."""
        safe_repo = _sanitize_for_filesystem(self.repo_name)
        return f"{safe_repo}_{self.step_name}_{self.unique_id}"
    
    @classmethod
    def parse_from_key(cls, storage_key: str) -> Optional['PromptDataKey']:
        """
        Parse a storage key back into a PromptDataKey object.
        
        Args:
            storage_key: The storage key string to parse
            
        Returns:
            PromptDataKey object or None if parsing fails
        """
        try:
            # Format: repo_step_uniqueid
            parts = storage_key.rsplit('_', 2)
            if len(parts) == 3:
                return cls(
                    repo_name=parts[0],
                    step_name=parts[1],
                    unique_id=parts[2]
                )
        except Exception:
            pass
        return None


class KeyNameCreator:
    """
    Centralized utility for creating consistent storage keys across providers.
    
    This class ensures that both DynamoDB and file-based storage use the same
    key naming conventions, making it easy to switch between storage backends.
    """
    
    @staticmethod
    def create_prompt_cache_key(
        repo_name: str,
        step_name: str,
        commit_sha: str,
        prompt_version: str = "1"
    ) -> PromptCacheKey:
        """
        Create a prompt cache key for storing/retrieving prompt analysis results.
        
        Args:
            repo_name: Repository name
            step_name: Analysis step/prompt name
            commit_sha: Git commit SHA
            prompt_version: Version of the prompt (default "1")
            
        Returns:
            PromptCacheKey object with methods to get storage and file-safe keys
        """
        return PromptCacheKey(
            repo_name=repo_name,
            step_name=step_name,
            commit_sha=commit_sha,
            prompt_version=prompt_version
        )
    
    @staticmethod
    def create_analysis_result_key(reference_key: str) -> AnalysisResultKey:
        """
        Create an analysis result key for storing/retrieving analysis results.
        
        Args:
            reference_key: Unique reference key for the result
            
        Returns:
            AnalysisResultKey object with methods to get storage and file-safe keys
        """
        return AnalysisResultKey(reference_key=reference_key)
    
    @staticmethod
    def create_investigation_metadata_key(
        repo_name: str,
        analysis_type: str = "investigation"
    ) -> InvestigationMetadataKey:
        """
        Create an investigation metadata key.
        
        Args:
            repo_name: Repository name
            analysis_type: Type of analysis (default "investigation")
            
        Returns:
            InvestigationMetadataKey object with methods to get storage and file-safe keys
        """
        return InvestigationMetadataKey(
            repo_name=repo_name,
            analysis_type=analysis_type
        )
    
    @staticmethod
    def create_prompt_data_key(
        repo_name: str,
        step_name: str,
        unique_id: str
    ) -> PromptDataKey:
        """
        Create a prompt data key for storing prompt content and context.
        
        Args:
            repo_name: Repository name
            step_name: Analysis step name
            unique_id: Unique identifier for this prompt data
            
        Returns:
            PromptDataKey object with methods to get storage and file-safe keys
        """
        return PromptDataKey(
            repo_name=repo_name,
            step_name=step_name,
            unique_id=unique_id
        )
    
    @staticmethod
    def create_dependencies_key(repo_name: str) -> AnalysisResultKey:
        """
        Create a key for storing dependencies data.
        
        Args:
            repo_name: Repository name
            
        Returns:
            AnalysisResultKey object with methods to get storage and file-safe keys
        """
        # Generate a unique identifier for dependencies
        import uuid
        import time
        unique_id = f"deps_{repo_name}_{int(time.time())}_{str(uuid.uuid4())[:8]}"
        return AnalysisResultKey(reference_key=unique_id)
    
    @staticmethod
    def parse_prompt_cache_key(storage_key: str) -> Optional[PromptCacheKey]:
        """
        Parse a storage key back into a PromptCacheKey object.
        
        Args:
            storage_key: The storage key string to parse
            
        Returns:
            PromptCacheKey object or None if parsing fails
        """
        return PromptCacheKey.parse_from_key(storage_key)
    
    @staticmethod
    def parse_analysis_result_key(storage_key: str) -> Optional[AnalysisResultKey]:
        """
        Parse a storage key back into an AnalysisResultKey object.
        
        Args:
            storage_key: The storage key string to parse
            
        Returns:
            AnalysisResultKey object or None if parsing fails
        """
        return AnalysisResultKey.parse_from_key(storage_key)
    
    @staticmethod
    def parse_investigation_metadata_key(storage_key: str) -> Optional[InvestigationMetadataKey]:
        """
        Parse a storage key back into an InvestigationMetadataKey object.
        
        Args:
            storage_key: The storage key string to parse
            
        Returns:
            InvestigationMetadataKey object or None if parsing fails
        """
        return InvestigationMetadataKey.parse_from_key(storage_key)
    
    @staticmethod
    def parse_prompt_data_key(storage_key: str) -> Optional[PromptDataKey]:
        """
        Parse a storage key back into a PromptDataKey object.
        
        Args:
            storage_key: The storage key string to parse
            
        Returns:
            PromptDataKey object or None if parsing fails
        """
        return PromptDataKey.parse_from_key(storage_key)
