"""
Main OpenCode Investigator module for repository analysis.

This module uses the OpenCode SDK to analyze repository structure with
support for multiple AI providers (Anthropic, OpenAI, Google, etc.).
"""

import os
import logging
import git
from typing import Optional, Dict, List, Union, Any
from urllib.parse import urlparse, urlunparse

try:
    # Try relative import first (when used as a module)
    from .core import (
        Config,
        Utils,
        GitRepositoryManager,
        RepositoryAnalyzer,
        FileManager,
        RepositoryTypeDetector
    )
    from .core.opencode_analyzer import OpenCodeAnalyzer
    from .core.opencode_server import OpenCodeServerManager
    from .activity_wrapper import ActivityWrapper
except ImportError:
    # Fall back to absolute import (when run directly)
    from core import (
        Config,
        Utils,
        GitRepositoryManager,
        RepositoryAnalyzer,
        FileManager,
        RepositoryTypeDetector
    )
    from core.opencode_analyzer import OpenCodeAnalyzer
    from core.opencode_server import OpenCodeServerManager
    from activity_wrapper import ActivityWrapper


class OpenCodeInvestigator:
    """
    A repository investigator that uses the OpenCode SDK to analyze repository structure.
    Supports multiple AI providers (Anthropic, OpenAI, Google, etc.).
    """

    def __init__(self, provider_id: Optional[str] = None, log_level: str = "INFO",
                 workflow_context: Optional[Any] = None):
        """
        Initialize the OpenCode investigator.

        Args:
            provider_id: AI provider ID (e.g., "anthropic", "openai", "google").
                        If not provided, will use PROVIDER_ID env var or default to "anthropic"
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
            workflow_context: Optional Temporal workflow context for activity execution
        """
        self._setup_logging(log_level)
        self.logger = logging.getLogger(__name__)

        # Get provider configuration
        self.provider_id = provider_id or Config.PROVIDER_ID

        self.logger.info(f"Initializing OpenCode Investigator (provider: {self.provider_id})")

        # Initialize OpenCode server manager (spawns server on-demand)
        self.server_manager = OpenCodeServerManager(port=Config.OPENCODE_PORT, logger=self.logger)

        # Initialize components
        self.git_manager = GitRepositoryManager(self.logger)
        self.repo_analyzer = RepositoryAnalyzer(self.logger)
        self.file_manager = FileManager(self.logger)
        self.type_detector = RepositoryTypeDetector(self.logger)

        # OpenCode analyzer will be initialized lazily when server is started
        self._opencode_analyzer = None

        # Initialize ActivityWrapper for Temporal activity execution
        self.activity_wrapper = ActivityWrapper(workflow_context)

        self.temp_dir = None
        self.logger.debug("OpenCode Investigator initialized successfully")

    @property
    def opencode_analyzer(self) -> OpenCodeAnalyzer:
        """Lazily initialize the OpenCode analyzer when first needed."""
        if self._opencode_analyzer is None:
            base_url = self.server_manager.start()
            self._opencode_analyzer = OpenCodeAnalyzer(base_url, self.provider_id, self.logger)
        return self._opencode_analyzer

    def _setup_logging(self, log_level: str):
        """Set up logging configuration."""
        level = getattr(logging, log_level.upper(), logging.INFO)
        
        # Check if logging is already configured to avoid conflicts in parallel execution
        if not logging.getLogger().handlers:
            formatter = logging.Formatter(Config.LOG_FORMAT, datefmt=Config.LOG_DATE_FORMAT)
            console_handler = logging.StreamHandler()
            console_handler.setLevel(level)
            console_handler.setFormatter(formatter)
            
            logging.basicConfig(
                level=level,
                handlers=[console_handler],
                format=Config.LOG_FORMAT
            )
        else:
            # If logging is already configured, just set the level
            logging.getLogger().setLevel(level)
    
    # ---------------------------------
    # Temporal activity heartbeat utils
    # ---------------------------------
    @staticmethod
    def _heartbeat_safe(details: Optional[str] = None) -> None:
        """Attempt to heartbeat if running inside a Temporal activity.

        This is a no-op when not executed inside an activity context, so
        investigator code can be reused outside Temporal without changes.
        """
        try:
            # Import locally to avoid hard dependency when used standalone
            from temporalio import activity as temporal_activity  # type: ignore
            # Heartbeat communicates liveness and also delivers cancellation
            temporal_activity.heartbeat(details or "progress")
        except Exception as e:
            # Safely ignore when not in an activity or heartbeat not available
            # log that we failed to heartbeat
            print(f"Failed to heartbeat: {str(e)}")
            pass
    
    def _sanitize_url_for_logging(self, url: str) -> str:
        """
        Remove sensitive information from URLs for safe logging.
        
        Args:
            url: URL that may contain authentication tokens or passwords
            
        Returns:
            Sanitized URL safe for logging
        """
        # If it's not a URL, return as is
        if not url or not url.startswith(('http://', 'https://')):
            return url
        
        parsed = urlparse(url)
        
        # Remove authentication info from the URL
        if parsed.username or parsed.password:
            # Reconstruct URL without auth
            sanitized_netloc = parsed.hostname or ''
            if parsed.port:
                sanitized_netloc += f":{parsed.port}"
            
            sanitized_url = urlunparse((
                parsed.scheme,
                sanitized_netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment
            ))
            
            # Add indication that auth was present
            return f"{sanitized_url} (authentication hidden)"
        
        # Check if GitHub token might be embedded
        github_token = os.getenv('GITHUB_TOKEN')
        if github_token and github_token in url:
            return url.replace(github_token, '***HIDDEN***')
        
        return url
    
    async def investigate_repository(self, repo_location: str, repo_type: Optional[str] = None) -> str:
        """
        Investigate a repository by cloning it and analyzing its structure with Claude.
        
        Args:
            repo_location: URL or path to the repository to investigate
            repo_type: Optional repository type override ('generic', 'backend', 'frontend', 'infra-as-code', 'libraries')
            
        Returns:
            Path to the generated {repository-name}-arch.md file
        """
        # Sanitize the URL for logging to hide sensitive information
        safe_url = self._sanitize_url_for_logging(repo_location)
        self.logger.info(f"Starting investigation of repository: {safe_url}")
        if repo_type:
            self.logger.info(f"Repository type override: {repo_type}")
        self._heartbeat_safe("start_investigation")
        
        try:
            # Step 1: Clone or update repository
            self.logger.info("Step 1: Cloning/updating repository")
            repo_path = self._prepare_repository(repo_location)
            self._heartbeat_safe("repository_prepared")
            
            # Step 1.5: Clean up any existing arch-docs folder
            self.logger.info("Step 1.5: Cleaning up existing arch-docs folder")
            self.file_manager.cleanup_arch_docs(repo_path)
            self._heartbeat_safe("cleanup_arch_docs_completed")
            
            # Step 2: Analyze repository structure
            self.logger.info("Step 2: Analyzing repository structure")
            repo_structure = self.repo_analyzer.get_structure(repo_path)
            self.logger.info(f"Repository structure captured ({len(repo_structure.split(chr(10)))} lines)")
            self._heartbeat_safe("repository_structure_captured")
            
            # Step 3: Run sequential analysis using prompts.json
            self.logger.info("Step 3: Running sequential analysis")
            final_analysis = await self._run_sequential_analysis(repo_path, repo_structure, repo_type, repo_location)
            self._heartbeat_safe("sequential_analysis_completed")
            
            # Step 4: Write final analysis to file
            self.logger.info("Step 4: Writing analysis to {repository-name}-arch.md")
            arch_file_path = self.file_manager.write_analysis(repo_path, final_analysis)
            self._heartbeat_safe("final_analysis_written")
            
            self.logger.info(f"Investigation completed successfully. Analysis saved to: {arch_file_path}")
            return arch_file_path
            
        except Exception as e:
            self.logger.error(f"Investigation failed: {str(e)}")
            raise Exception(f"Failed to investigate repository: {str(e)}")
    
    def _build_context_from_config(self, context_config: Optional[Union[Dict, List[Dict]]], step_results: Dict[str, str]) -> str:
        """
        Build context string from context configuration.
        
        Args:
            context_config: Context configuration (can be dict, list, or None)
            step_results: Dictionary of previous step results
            
        Returns:
            Combined context string
        """
        if not context_config:
            return ""
        
        context_parts = []
        
        # Handle both array and single dict for backward compatibility
        context_items = context_config if isinstance(context_config, list) else [context_config]
        
        for context_item in context_items:
            context_part = self._process_single_context_item(context_item, step_results)
            if context_part:
                context_parts.append(context_part)
        
        return "".join(context_parts)
    
    def _process_single_context_item(self, context_item: Dict, step_results: Dict[str, str]) -> str:
        """
        Process a single context item and return the formatted context.
        
        Args:
            context_item: Single context configuration item
            step_results: Dictionary of previous step results
            
        Returns:
            Formatted context string or empty string if not found
        """
        if not isinstance(context_item, dict):
            return ""
        
        context_type = context_item.get("type", "")
        context_val = context_item.get("val", "")
        
        if context_type == "step":
            return self._get_step_context(context_val, step_results)
        
        # Future context types can be added here
        self.logger.debug(f"Unknown context type: '{context_type}'")
        return ""
    
    def _get_step_context(self, step_name: str, step_results: Dict[str, str]) -> str:
        """
        Get context from a previous step result.
        
        Args:
            step_name: Name of the step to get context from
            step_results: Dictionary of previous step results
            
        Returns:
            Formatted step context or empty string if not found
        """
        if step_name in step_results:
            self.logger.debug(f"Using context from step: {step_name}")
            return f"\n\n## {step_name} Results\n\n{step_results[step_name]}"
        
        self.logger.debug(f"Context step '{step_name}' not found")
        return ""
    
    def _build_exact_prompt(self, prompt_template: str, repo_structure: str, previous_context: str) -> str:
        """
        Build the exact prompt that will be sent to Claude.
        This replicates the logic from OpenCodeAnalyzer.analyze_with_context()
        
        Args:
            prompt_template: The prompt template with placeholders
            repo_structure: The repository structure to insert
            previous_context: Any previous context to include
            
        Returns:
            The exact prompt string that will be sent to Claude
        """
        # Replace placeholders in the prompt
        prompt = prompt_template.replace("{repo_structure}", repo_structure)
        
        # Add previous context if available
        if previous_context:
            context_section = f"\n\n## Previous Analysis Context\n\n{previous_context}\n\n"
            prompt = prompt.replace("{previous_context}", context_section)
        else:
            # Remove the placeholder if no context
            prompt = prompt.replace("{previous_context}", "")
        
        return prompt
    
    async def _process_analysis_step(self, step: Dict, prompts_dir: str, repo_structure: str, step_results: Dict[str, str]) -> Optional[Dict]:
        """
        Process a single analysis step.
        
        Args:
            step: Step configuration
            prompts_dir: Directory containing prompt files
            repo_structure: Repository structure string
            step_results: Dictionary of previous step results
            
        Returns:
            Result dictionary or None if step was skipped
        """
        step_name = step.get("name", "unknown")
        file_name = step.get("file", "")
        is_required = step.get("required", True)
        description = step.get("description", "")
        context_config = step.get("context", None)
        
        self.logger.info(f"Processing step: {step_name} - {description}")
        # Heartbeat before starting a potentially long step
        self._heartbeat_safe(f"step_start:{step_name}")
        
        # Read the prompt file
        prompt_content = self.file_manager.read_prompt_file(prompts_dir, file_name)
        
        if prompt_content is None:
            if is_required:
                self.logger.error(f"Required prompt file not found: {file_name}")
                raise Exception(f"Required prompt file not found: {file_name}")
            else:
                self.logger.warning(f"Optional prompt file not found, skipping: {file_name}")
                return None
        
        # Build context from configuration
        context_to_use = self._build_context_from_config(context_config, step_results)
        
        # Run analysis
        self.logger.info(f"Running analysis for: {step_name}")
        try:
            # Get the exact prompt that will be sent to Claude
            exact_prompt = self._build_exact_prompt(prompt_content, repo_structure, context_to_use)
            
            # Save the exact prompt that's being sent to Claude
            prompt_path = self.file_manager.write_prompt_file(
                self.temp_dir, 
                step_name, 
                exact_prompt
            )
            self.logger.debug(f"Exact prompt saved to: {prompt_path}")
            
            # Execute Claude analysis via Temporal activity when in workflow context
            if self.activity_wrapper.is_temporal_context():
                # Import the activity function
                from activities.investigate_activities import analyze_with_claude
                from temporalio.common import RetryPolicy
                from datetime import timedelta
                
                result = await self.activity_wrapper.execute_activity(
                    analyze_with_claude,
                    prompt_content,
                    repo_structure,
                    context_to_use,
                    start_to_close_timeout=timedelta(minutes=15),
                    retry_policy=RetryPolicy(
                        maximum_attempts=3,
                        initial_interval=timedelta(seconds=5),
                        maximum_interval=timedelta(seconds=30),
                        backoff_coefficient=2.0
                    )
                )
            else:
                # Fallback to direct execution when not in Temporal context
                result = self.opencode_analyzer.analyze_with_context(
                    prompt_content,
                    repo_structure,
                    context_to_use
                )
            
            # Save intermediate result
            result_path = self.file_manager.write_intermediate_result(
                self.temp_dir, 
                step_name, 
                result
            )
            self.logger.debug(f"Intermediate result saved to: {result_path}")
            # Heartbeat after finishing the step
            self._heartbeat_safe(f"step_done:{step_name}")
            
            return {
                "name": step_name,
                "description": description,
                "content": result
            }
            
        except Exception as e:
            if is_required:
                self.logger.error(f"Failed to process required step {step_name}: {str(e)}")
                raise
            else:
                self.logger.warning(f"Failed to process optional step {step_name}: {str(e)}")
                return None
    
    async def _run_sequential_analysis(self, repo_path: str, repo_structure: str, repo_type: Optional[str] = None, repo_url: Optional[str] = None) -> str:
        """Run sequential analysis using prompts from prompts.json."""
        # Get repository type (use override if provided, otherwise default to generic)
        self.logger.info("Determining repository type...")
        prompts_dir = self.type_detector.get_prompts_directory(repo_path, repo_type, repo_url)
        self.logger.info(f"Using prompts from: {prompts_dir}")
        
        # Read prompts configuration
        prompts_config = self.file_manager.read_prompts_config(prompts_dir)
        processing_order = prompts_config.get("processing_order", [])
        
        # Sort by order field
        processing_order.sort(key=lambda x: x.get("order", 999))
        
        # Initialize results storage
        step_results = {}
        all_results = []
        
        for step in processing_order:
            result = await self._process_analysis_step(step, prompts_dir, repo_structure, step_results)
            
            if result:
                # Store result for potential context use
                step_results[result["name"]] = result["content"]
                all_results.append(result)
            # Heartbeat after each loop iteration regardless of result
            self._heartbeat_safe("sequential_step_progress")
        
        # Format all results into a comprehensive document
        final_analysis = self._format_final_analysis(all_results)
        self._heartbeat_safe("sequential_analysis_formatted")
        return final_analysis
    
    def _format_final_analysis(self, all_results: List[Dict]) -> str:
        """Format all analysis results into a comprehensive document."""
        sections = []
        
        # Add table of contents
        toc = "## Table of Contents\n\n"
        for i, result in enumerate(all_results, 1):
            name = result["name"].replace("_", " ").title()
            toc += f"{i}. [{name}](#{result['name']})\n"
        
        sections.append(toc)
        
        # Add each analysis section
        for result in all_results:
            section_title = result["name"].replace("_", " ").title()
            section_content = f"## {section_title} {{#{result['name']}}}\n\n"
            
            if result["description"]:
                section_content += f"*{result['description']}*\n\n"
            
            section_content += result["content"]
            sections.append(section_content)
        
        # Join all sections with proper spacing
        return "\n\n---\n\n".join(sections)
    
    def _prepare_repository(self, repo_location: str) -> str:
        """Prepare repository by cloning or updating it."""
        # Setup directories - use project root instead of investigator folder
        investigator_root = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(investigator_root))  # Go up two levels from src/investigator/
        temp_root = os.path.join(project_root, Config.TEMP_DIR)
        os.makedirs(temp_root, exist_ok=True)
        
        # Extract repository name and create target directory
        repo_name = Utils.extract_repo_name(repo_location)
        
        # Create unique directory name to prevent conflicts in parallel execution
        import uuid
        unique_id = str(uuid.uuid4())[:8]  # Use first 8 characters of UUID
        repo_dir = os.path.join(temp_root, f"{repo_name}_{unique_id}")
        self.temp_dir = repo_dir
        
        self.logger.debug(f"Using unique temp directory: {self.temp_dir}")
        
        # Clone or update repository
        try:
            repo_path = self.git_manager.clone_or_update(repo_location, repo_dir)
        except git.exc.GitCommandError:
            # If update failed, clone fresh
            repo_path = self.git_manager.clone_or_update(repo_location, repo_dir)
        
        # Log repository size
        repo_size = Utils.get_directory_size(repo_path)
        self.logger.info(f"Repository size: {repo_size}")
        
        return repo_path


# Backwards compatibility alias
ClaudeInvestigator = OpenCodeInvestigator


async def investigate_repo(repo_location: str, provider_id: Optional[str] = None, log_level: str = "INFO", repo_type: Optional[str] = None) -> str:
    """
    Convenience function to investigate a repository.

    Args:
        repo_location: URL or path to the repository to investigate
        provider_id: AI provider ID (optional, defaults to Config.PROVIDER_ID)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        repo_type: Optional repository type override ('generic', 'backend', 'frontend', 'mobile', 'infra-as-code', 'libraries')

    Returns:
        Path to the generated {repository-name}-arch.md file
    """
    investigator = OpenCodeInvestigator(provider_id=provider_id, log_level=log_level)
    return await investigator.investigate_repository(repo_location, repo_type=repo_type)


if __name__ == "__main__":
    import sys
    import asyncio

    if len(sys.argv) < 2:
        print("Usage: python investigator.py <repository_location> [provider_id] [log_level]")
        print("Provider IDs: anthropic (default), openai, google, bedrock, etc.")
        print("Log levels: DEBUG, INFO, WARNING, ERROR (default: INFO)")
        sys.exit(1)

    repo_location = sys.argv[1]
    provider_id = sys.argv[2] if len(sys.argv) > 2 else None
    log_level = sys.argv[3] if len(sys.argv) > 3 else "INFO"

    try:
        arch_file_path = asyncio.run(investigate_repo(repo_location, provider_id, log_level))
        print(f"Investigation complete! Analysis saved to: {arch_file_path}")
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
