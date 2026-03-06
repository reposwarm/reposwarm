"""
File-based implementation of prompt context storage.

This module provides file-based storage for prompt contexts and analysis results,
primarily used for local development and testing without DynamoDB.
"""

import os
import json
import uuid
import shutil
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

from .prompt_context_base import PromptContextBase, PromptContextManagerBase
from .storage_keys import KeyNameCreator

logger = logging.getLogger(__name__)


@dataclass
class FileBasedPromptContext(PromptContextBase):
    """
    File-based implementation of PromptContext.
    
    Stores all data in local files for testing and development.
    """
    
    _storage_dir: Path = field(default=None, init=False, repr=False)
    
    def __post_init__(self):
        """Initialize storage directory after dataclass initialization."""
        if self._storage_dir is None:
            # Use the project's temp directory for local file storage
            # Check if PROMPT_CONTEXT_STORAGE_DIR is set, otherwise use project's temp folder
            if os.environ.get('PROMPT_CONTEXT_STORAGE_DIR'):
                base_dir = os.environ.get('PROMPT_CONTEXT_STORAGE_DIR')
            else:
                # Get the project root (where this script is located)
                project_root = Path(__file__).parent.parent.parent  # Go up from src/utils/ to project root
                base_dir = project_root / 'temp' / 'prompt_context_storage'
            
            self._storage_dir = Path(base_dir) / self._safe_repo_name()
            self._storage_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Using file storage at: {self._storage_dir}")
    
    def _safe_repo_name(self) -> str:
        """Sanitize repo name for filesystem use (handles URLs)."""
        import re
        name = self.repo_name
        for prefix in ('https://', 'http://', 'git@', 'ssh://'):
            if name.startswith(prefix):
                name = name[len(prefix):]
                break
        name = re.sub(r'[/\\:*?"<>|@#]', '_', name)
        name = re.sub(r'_+', '_', name)
        return name.strip('_.')
    
    def _get_file_path(self, key: str) -> Path:
        """Get the file path for a given key."""
        return self._storage_dir / f"{key}.json"
    
    def save_prompt_data(self, prompt_content: str, repo_structure: str, ttl_minutes: int = 60) -> str:
        """
        Save prompt and repository structure to files.
        
        Args:
            prompt_content: The prompt template content
            repo_structure: Repository structure string
            ttl_minutes: TTL for the data in minutes (ignored in file implementation)
            
        Returns:
            Reference key for the saved data
        """
        # Generate unique reference key using KeyNameCreator
        unique_id = str(uuid.uuid4())[:8]
        key_obj = KeyNameCreator.create_prompt_data_key(
            repo_name=self.repo_name,
            step_name=self.step_name,
            unique_id=unique_id
        )
        self.data_reference_key = key_obj.to_file_safe_key()
        
        logger.info(f"Saving prompt data to file with key: {self.data_reference_key}")
        
        # Save to file using file-safe key
        data = {
            "prompt_content": prompt_content,
            "repo_structure": repo_structure,
            "step_name": self.step_name,
            "repo_name": self.repo_name
        }
        
        file_path = self._get_file_path(self.data_reference_key)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Saved prompt data to: {file_path}")
        return self.data_reference_key
    
    def get_prompt_and_context(self) -> Dict[str, Any]:
        """
        Retrieve prompt data and context from files.
        
        Returns:
            Dictionary containing prompt_content, repo_structure, and context
        """
        if not self.data_reference_key:
            raise ValueError("No data reference key set. Call save_prompt_data first.")
        
        logger.info(f"Retrieving prompt data from file with key: {self.data_reference_key}")
        
        # Get main prompt data
        file_path = self._get_file_path(self.data_reference_key)
        if not file_path.exists():
            raise Exception(f"No data file found for key: {self.data_reference_key}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            temp_data = json.load(f)
        
        prompt_content = temp_data.get('prompt_content')
        repo_structure = temp_data.get('repo_structure')
        
        # Build context from reference keys
        context = None
        if self.context_reference_keys:
            logger.info(f"Building context from {len(self.context_reference_keys)} references")
            context_parts = []
            
            for context_key in self.context_reference_keys:
                result_file = self._get_file_path(context_key)
                if result_file.exists():
                    with open(result_file, 'r', encoding='utf-8') as f:
                        result_data = json.load(f)
                        result = result_data.get('result_content')
                        if result:
                            # Extract step name from key for better formatting
                            parts = context_key.split('_')
                            step_name = parts[1] if len(parts) > 1 else context_key
                            context_parts.append(f"## {step_name}\n\n{result}")
                else:
                    logger.warning(f"No result file found for context key: {context_key}")
            
            if context_parts:
                context = "\n\n".join(context_parts)
        
        return {
            "prompt_content": prompt_content,
            "repo_structure": repo_structure,
            "context": context
        }
    
    def get_result(self) -> Optional[str]:
        """
        Retrieve the analysis result from file.
        
        Returns:
            The result content or None if not found
        """
        if not self.result_reference_key:
            logger.warning("No result reference key set")
            return None
        
        file_path = self._get_file_path(self.result_reference_key)
        if not file_path.exists():
            logger.warning(f"No result file found for key: {self.result_reference_key}")
            return None
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('result_content')
    
    def cleanup(self):
        """
        Clean up all temporary files associated with this context.
        """
        files_to_cleanup = []
        
        if self.data_reference_key:
            files_to_cleanup.append(self._get_file_path(self.data_reference_key))
        
        if self.result_reference_key:
            files_to_cleanup.append(self._get_file_path(self.result_reference_key))
        
        for file_path in files_to_cleanup:
            try:
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"Cleaned up file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup {file_path}: {str(e)}")
        
        # Clean up directory if empty
        try:
            if self._storage_dir.exists() and not any(self._storage_dir.iterdir()):
                self._storage_dir.rmdir()
                logger.info(f"Removed empty directory: {self._storage_dir}")
        except Exception as e:
            logger.warning(f"Failed to cleanup directory: {str(e)}")


class FileBasedPromptContextManager(PromptContextManagerBase):
    """
    File-based implementation of PromptContextManager.
    """
    
    def __init__(self, repo_name: str):
        """
        Initialize the manager for a repository.
        
        Args:
            repo_name: Name of the repository being analyzed
        """
        super().__init__(repo_name)
        # Ensure storage directory exists
        # Use the project's temp directory for local file storage
        if os.environ.get('PROMPT_CONTEXT_STORAGE_DIR'):
            base_dir = os.environ.get('PROMPT_CONTEXT_STORAGE_DIR')
        else:
            # Get the project root (where this script is located)
            project_root = Path(__file__).parent.parent.parent  # Go up from src/utils/ to project root
            base_dir = project_root / 'temp' / 'prompt_context_storage'
        
        self._storage_dir = Path(base_dir) / self._safe_repo_name(repo_name)
        self._storage_dir.mkdir(parents=True, exist_ok=True)
    
    @staticmethod
    def _safe_repo_name(name: str) -> str:
        """Sanitize repo name for filesystem use (handles URLs)."""
        import re
        for prefix in ('https://', 'http://', 'git@', 'ssh://'):
            if name.startswith(prefix):
                name = name[len(prefix):]
                break
        name = re.sub(r'[/\\:*?"<>|@#]', '_', name)
        name = re.sub(r'_+', '_', name)
        return name.strip('_.')

    def create_context_for_step(self, step_name: str, context_config: List = None) -> FileBasedPromptContext:
        """
        Create a new file-based context for an analysis step with proper context references.
        
        Args:
            step_name: Name of the analysis step
            context_config: Configuration for which previous steps to include as context
            
        Returns:
            New FileBasedPromptContext instance
        """
        context = FileBasedPromptContext.create_for_step(self.repo_name, step_name)
        
        # Add context references based on configuration
        if context_config:
            for context_step in context_config:
                # Handle both string and dict formats
                if isinstance(context_step, dict):
                    step_ref = context_step.get("val")
                else:
                    step_ref = context_step
                
                if step_ref and step_ref in self.step_results:
                    context.add_context_reference(self.step_results[step_ref])
        
        self.contexts[step_name] = context
        return context
    
    def retrieve_all_results(self) -> Dict[str, str]:
        """
        Retrieve all results from files.
        
        Returns:
            Dictionary mapping step names to their result content
        """
        results = {}
        
        for step_name, result_key in self.step_results.items():
            # Use KeyNameCreator to generate the correct file-safe key with _result_ prefix
            result_key_obj = KeyNameCreator.create_analysis_result_key(result_key)
            file_safe_key = result_key_obj.to_file_safe_key()
            
            file_path = self._storage_dir / f"{file_safe_key}.json"
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    content = data.get('result_content')
                    if content:
                        results[step_name] = content
                    else:
                        logger.warning(f"No content in file for step {step_name}")
            else:
                logger.warning(f"No result file found for step {step_name}: {file_path}")
        
        return results
    
    def cleanup_all(self):
        """Clean up all contexts and the storage directory."""
        super().cleanup_all()
        
        # Clean up the entire storage directory for this repo
        try:
            if self._storage_dir.exists():
                shutil.rmtree(self._storage_dir)
                logger.info(f"Cleaned up storage directory: {self._storage_dir}")
        except Exception as e:
            logger.warning(f"Failed to cleanup storage directory: {str(e)}")
    
    def save_analysis_result(self, reference_key: str, result_content: str, 
                           step_name: str = None, ttl_minutes: int = 60) -> Dict[str, Any]:
        """
        Save analysis result to file storage.
        
        Args:
            reference_key: Unique reference key for this result
            result_content: The analysis result content
            step_name: Optional step name for tracking
            ttl_minutes: TTL in minutes (ignored in file implementation)
        
        Returns:
            Dictionary with save status
        """
        try:
            # Use KeyNameCreator to generate file-safe key
            result_key_obj = KeyNameCreator.create_analysis_result_key(reference_key)
            file_safe_key = result_key_obj.to_file_safe_key()
            
            # Save to file
            data = {
                "result_content": result_content,
                "step_name": step_name,
                "reference_key": reference_key,
                "timestamp": os.path.getmtime(__file__)  # Use current time
            }
            
            file_path = self._storage_dir / f"{file_safe_key}.json"
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Saved analysis result to: {file_path}")
            
            return {
                "status": "success",
                "reference_key": reference_key,
                "timestamp": data["timestamp"]
            }
        except Exception as e:
            logger.error(f"Failed to save analysis result: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def get_analysis_result(self, reference_key: str) -> Optional[str]:
        """
        Retrieve analysis result from file storage.
        
        Args:
            reference_key: The unique reference key for the result
        
        Returns:
            The result content string or None if not found
        """
        try:
            # Use KeyNameCreator to generate file-safe key
            result_key_obj = KeyNameCreator.create_analysis_result_key(reference_key)
            file_safe_key = result_key_obj.to_file_safe_key()
            
            file_path = self._storage_dir / f"{file_safe_key}.json"
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('result_content')
            else:
                logger.debug(f"No result file found for key: {reference_key}")
                return None
        except Exception as e:
            logger.error(f"Failed to retrieve analysis result: {str(e)}")
            return None
    
    def save_investigation_metadata(self, repository_name: str, repository_url: str,
                                   latest_commit: str, branch_name: str,
                                   analysis_type: str = "investigation",
                                   analysis_data: Dict[str, Any] = None,
                                   ttl_days: int = 90) -> Dict[str, Any]:
        """
        Save investigation metadata to file storage.
        
        Args:
            repository_name: Name of the repository
            repository_url: URL of the repository
            latest_commit: Latest commit SHA
            branch_name: Branch name
            analysis_type: Type of analysis
            analysis_data: Additional analysis data
            ttl_days: TTL in days (ignored in file implementation)
        
        Returns:
            Dictionary with save status
        """
        try:
            # Use KeyNameCreator to generate file-safe key
            metadata_key_obj = KeyNameCreator.create_investigation_metadata_key(
                repo_name=repository_name,
                analysis_type=analysis_type
            )
            file_safe_key = metadata_key_obj.to_file_safe_key()
            
            # Prepare metadata
            import time
            metadata = {
                "repository_name": repository_name,
                "repository_url": repository_url,
                "latest_commit": latest_commit,
                "branch_name": branch_name,
                "analysis_type": analysis_type,
                "analysis_timestamp": time.time(),
                "analysis_data": analysis_data or {}
            }
            
            # Include prompt metadata if provided
            if analysis_data and 'prompt_metadata' in analysis_data:
                metadata['prompt_metadata'] = analysis_data['prompt_metadata']
            
            # Save to file
            file_path = self._storage_dir / f"{file_safe_key}.json"
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Saved investigation metadata to: {file_path}")
            
            return metadata
        except Exception as e:
            logger.error(f"Failed to save investigation metadata: {str(e)}")
            raise
    
    def get_latest_investigation(self, repository_name: str) -> Optional[Dict[str, Any]]:
        """
        Get the latest investigation metadata for a repository.
        
        Args:
            repository_name: Name of the repository
        
        Returns:
            Investigation metadata dictionary or None if not found
        """
        try:
            # Use KeyNameCreator to generate file-safe key
            metadata_key_obj = KeyNameCreator.create_investigation_metadata_key(
                repo_name=repository_name,
                analysis_type="investigation"
            )
            file_safe_key = metadata_key_obj.to_file_safe_key()
            
            file_path = self._storage_dir / f"{file_safe_key}.json"
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                logger.debug(f"No investigation metadata found for: {repository_name}")
                return None
        except Exception as e:
            logger.error(f"Failed to retrieve investigation metadata: {str(e)}")
            return None
