import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from temporalio import workflow
from temporalio.common import RetryPolicy
from datetime import timedelta, datetime
from typing import Dict, Optional
import logging
import uuid

from activities.investigate_activities import (
    save_to_arch_hub,
    clone_repository_activity,
    analyze_repository_structure_activity, 
    get_prompts_config_activity,
    read_prompt_file_activity,
    save_prompt_context_activity,
    analyze_with_claude_context,
    retrieve_all_results_activity,
    write_analysis_result_activity,
    cleanup_repository_activity,
    read_dependencies_activity,
    cache_dependencies_activity
)
from activities.investigation_cache_activities import (
    check_if_repo_needs_investigation,
    save_investigation_metadata
)
from activities.dynamodb_health_check_activity import check_dynamodb_health
from investigator.core.analysis_results_collector import AnalysisResultsCollector
from models import (
    AnalyzeWithClaudeInput, 
    PromptContextDict, 
    ClaudeConfigOverrides, 
    CacheCheckInput, 
    SaveMetadataInput,
    InvestigateSingleRepoRequest,
    InvestigateSingleRepoResult,
    CloneRepositoryResult,
    PromptsConfigResult,
    ProcessAnalysisResult,
    WriteResultsOutput,
    SaveToHubResult,
    SaveToDynamoResult,
    ConfigOverrides,
    InvestigationResult
)

logger = logging.getLogger(__name__)


@workflow.defn
class InvestigateSingleRepoWorkflow:
    """Child workflow that wraps a single-repo investigation activity."""
    
    def __init__(self) -> None:
        self._status = "initialized"
        self._last_heartbeat = None
        self._investigation_progress = None
        self._repo_name = None
        self._current_step = 0
        self._total_steps = 8  # health_check, clone, cache, structure, prompts, deps, analyze, write
        self._step_name = "initialized"

    @workflow.query
    def get_progress(self) -> dict:
        """Query to get current workflow progress."""
        return {
            "current_step": self._current_step,
            "total_steps": self._total_steps,
            "step_name": self._step_name,
            "status": self._status,
            "repo_name": self._repo_name
        }

    @workflow.query
    def get_status(self) -> str:
        """Query to get current workflow status."""
        return self._status

    async def _perform_health_check(self) -> None:
        """Perform DynamoDB health check before starting investigation."""
        self._current_step = 1
        self._step_name = "health_check"
        self._status = "health_check"
        self._last_heartbeat = workflow.now()
        logger.info("Performing DynamoDB health check before starting investigation")
        
        health_check_result = await workflow.execute_activity(
            check_dynamodb_health,
            args=[],
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(
                maximum_attempts=3,  # Fail after 3 attempts as requested
                initial_interval=timedelta(seconds=10),  # 10 seconds apart as requested
                maximum_interval=timedelta(seconds=10),   # Keep at 10 seconds to maintain consistent intervals
                backoff_coefficient=1.0,  # No backoff to maintain 10 second intervals
                non_retryable_error_types=["ImportError"]  # Don't retry import errors
            ),
        )
        
        if health_check_result.get("status") != "healthy":
            error_msg = f"DynamoDB health check failed: {health_check_result.get('message', 'Unknown error')}"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        logger.info(f"DynamoDB health check passed: {health_check_result.get('message')}")

    async def _clone_repository(self, repo_url: str, repo_name: str) -> CloneRepositoryResult:
        """Clone the repository and return clone results."""
        self._current_step = 2
        self._step_name = "cloning"
        self._status = "cloning"
        self._last_heartbeat = workflow.now()
        
        clone_result = await workflow.execute_activity(
            clone_repository_activity,
            args=[repo_url, repo_name],
            start_to_close_timeout=timedelta(minutes=3),
            retry_policy=RetryPolicy(
                maximum_attempts=3,
                initial_interval=timedelta(seconds=5),
                maximum_interval=timedelta(minutes=1),
            ),
        )
        
        # Convert dict result to Pydantic model
        return CloneRepositoryResult(
            repo_path=clone_result["repo_path"],
            temp_dir=clone_result["temp_dir"],
            status=clone_result.get("status", "success"),
            message=clone_result.get("message")
        )

    async def _check_cache(self, repo_name: str, repo_url: str, repo_path: str, prompt_versions: Optional[Dict[str, str]] = None) -> Dict:
        """Check if repository needs investigation using DynamoDB cache."""
        workflow.logger.info(f"🔍 WORKFLOW: Starting cache check for {repo_name}")
        workflow.logger.info(f"   repo_url: {repo_url}")
        workflow.logger.info(f"   repo_path: {repo_path}")
        if prompt_versions:
            workflow.logger.info(f"   prompt_versions: {len(prompt_versions)} prompts provided")
        else:
            workflow.logger.warning(f"   ⚠️  NO PROMPT VERSIONS provided to cache check")
        
        self._current_step = 3
        self._step_name = "checking_cache"
        self._status = "checking_cache"
        self._last_heartbeat = workflow.now()
        
        # Create Pydantic input model for cache check
        cache_check_input = CacheCheckInput(
            repo_name=repo_name,
            repo_url=repo_url,
            repo_path=repo_path,
            prompt_versions=prompt_versions
        )
        
        cache_check_result = await workflow.execute_activity(
            check_if_repo_needs_investigation,
            args=[cache_check_input],
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=RetryPolicy(
                maximum_attempts=2,
                initial_interval=timedelta(seconds=2),
                maximum_interval=timedelta(seconds=10),
            ),
        )
        
        workflow.logger.info(f"🎯 WORKFLOW: Cache check result: needs_investigation={cache_check_result.needs_investigation}")
        workflow.logger.info(f"   reason: {cache_check_result.reason}")
        workflow.logger.info(f"   latest_commit: {cache_check_result.latest_commit or 'None'}")
        
        return cache_check_result

    async def _analyze_repository_structure(self, repo_path: str) -> Dict:
        """Analyze the repository structure."""
        self._current_step = 4
        self._step_name = "analyzing_structure"
        self._status = "analyzing_structure"
        self._last_heartbeat = workflow.now()
        
        structure_result = await workflow.execute_activity(
            analyze_repository_structure_activity,
            args=[repo_path],
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(
                maximum_attempts=2,
                initial_interval=timedelta(seconds=5),
                maximum_interval=timedelta(seconds=30),
            ),
        )
        return structure_result

    async def _get_prompts_config(self, repo_path: str, repo_type: str, repo_url: str) -> PromptsConfigResult:
        """Get prompts configuration for the repository."""
        self._current_step = 5
        self._step_name = "getting_prompts"
        self._status = "getting_prompts"
        self._last_heartbeat = workflow.now()
        
        prompts_result = await workflow.execute_activity(
            get_prompts_config_activity,
            args=[repo_path, repo_type, repo_url],
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(
                maximum_attempts=2,
                initial_interval=timedelta(seconds=5),
                maximum_interval=timedelta(seconds=30),
            ),
        )
        
        # Convert dict result to Pydantic model
        return PromptsConfigResult(
            prompts_dir=prompts_result["prompts_dir"],
            processing_order=prompts_result["processing_order"],
            prompt_versions=prompts_result.get("prompt_versions", {}),
            status=prompts_result.get("status", "success")
        )

    async def _read_and_cache_dependencies(self, repo_path: str) -> dict:
        """Read dependency files and cache them."""
        self._current_step = 6
        self._step_name = "reading_dependencies"
        self._status = "reading_dependencies"
        self._last_heartbeat = workflow.now()
        
        logger.info(f"Reading and caching dependencies for repository at: {repo_path}")
        
        # Read and format dependencies
        deps_data = await workflow.execute_activity(
            read_dependencies_activity,
            args=[repo_path],
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=RetryPolicy(
                maximum_attempts=2,
                initial_interval=timedelta(seconds=2),
                maximum_interval=timedelta(seconds=10),
            ),
        )
        
        if deps_data["status"] != "success":
            logger.warning(f"Failed to read dependencies: {deps_data.get('message', 'Unknown error')}")
            return {
                "deps_reference_key": None,
                "formatted_content": "Error reading dependency files!"
            }
        
        logger.info(f"Dependencies read successfully: {deps_data['message']}")
        
        # Cache the dependencies data if we found any
        if deps_data["raw_dependencies"]:
            cache_result = await workflow.execute_activity(
                cache_dependencies_activity,
                args=[self._repo_name, deps_data["raw_dependencies"]],
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=RetryPolicy(
                    maximum_attempts=2,
                    initial_interval=timedelta(seconds=2),
                    maximum_interval=timedelta(seconds=10),
                ),
            )
            
            if cache_result["status"] == "success":
                logger.info(f"Dependencies cached successfully with key: {cache_result['deps_reference_key']}")
                return {
                    "deps_reference_key": cache_result["deps_reference_key"],
                    "formatted_content": deps_data["formatted_content"]
                }
            else:
                logger.warning(f"Failed to cache dependencies: {cache_result.get('error', 'Unknown error')}")
        
        # Return formatted content even if caching failed or no dependencies found
        return {
            "deps_reference_key": None,
            "formatted_content": deps_data["formatted_content"]
        }

    async def _process_analysis_steps(self, processing_order: list, prompts_dir: str, repo_structure: Dict, config_overrides: ConfigOverrides = None, deps_formatted_content: str = None) -> ProcessAnalysisResult:
        """Process each analysis step using PromptContext for cleaner abstraction."""
        if config_overrides is None:
            config_overrides = ConfigOverrides()

        self._current_step = 7
        self._step_name = "analyzing"
        self._status = "analyzing"
        self._last_heartbeat = workflow.now()
        
        # Initialize the results collector with base prompts config
        # Load base prompts config for validation
        import json
        from pathlib import Path
        try:
            base_prompts_path = Path(__file__).parent.parent / "prompts" / "base_prompts.json"
            with open(base_prompts_path, 'r') as f:
                base_prompts_config = json.load(f)
        except Exception as e:
            logger.warning(f"Could not load base prompts config: {e}")
            base_prompts_config = None
        
        results_collector = AnalysisResultsCollector(self._repo_name, base_prompts_config)
        
        # Track step results for building context
        step_results = {}  # Maps step names to result reference keys
        all_result_info = []   # Stores metadata about results
        cached_steps = 0
        
        for step in processing_order:
            step_name = step.get("name", "unknown")
            file_name = step.get("file", "")
            is_required = True
            description = step.get("description", "")
            context_config = step.get("context", None)
            
            logger.info(f"Processing step: {step_name} - {description}")
            
            # Read the prompt file
            prompt_result = await workflow.execute_activity(
                read_prompt_file_activity,
                args=[prompts_dir, file_name],
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=RetryPolicy(
                    maximum_attempts=2,
                    initial_interval=timedelta(seconds=1),
                    maximum_interval=timedelta(seconds=10),
                ),
            )
            
            if prompt_result["status"] == "not_found":
                if is_required:
                    logger.error(f"Required prompt file not found: {file_name}")
                    raise Exception(f"Required prompt file not found: {file_name}")
                else:
                    logger.warning(f"Optional prompt file not found, skipping: {file_name}")
                    continue
            
            prompt_content = prompt_result["prompt_content"]
            prompt_version = prompt_result.get("prompt_version", "1")
            
            # Create PromptContext for this step with proper context references
            context_dict = {
                "repo_name": self._repo_name,
                "step_name": step_name,
                "prompt_version": prompt_version,
                "context_reference_keys": []
            }
            
            # Add context references from previous steps
            if context_config:
                for context_step in context_config:
                    # Handle both string and dict formats
                    if isinstance(context_step, dict) and "val" in context_step:
                        step_ref = context_step["val"]
                    else:
                        step_ref = context_step
                    
                    if step_ref and step_ref in step_results:
                        result_key = step_results[step_ref]
                        # Only add non-None result keys
                        if result_key is not None:
                            context_dict["context_reference_keys"].append(result_key)
                        else:
                            logger.warning(f"Step {step_ref} has None result key, skipping from context")
            
            # Save prompt data to DynamoDB using PromptContext
            logger.info(f"Saving prompt data for step: {step_name}")
            save_result = await workflow.execute_activity(
                save_prompt_context_activity,
                args=[context_dict, prompt_content, repo_structure, deps_formatted_content],
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=RetryPolicy(
                    maximum_attempts=2,
                    initial_interval=timedelta(seconds=1),
                    maximum_interval=timedelta(seconds=10),
                ),
            )
            
            if save_result["status"] != "success":
                raise Exception(f"Failed to save prompt context for step {step_name}")
            
            # Get updated context with data reference key
            updated_context = save_result["context"]
            
            # Execute Claude analysis using PromptContext with prompt-level caching
            logger.info(f"Calling Claude for step: {step_name}")
            # Get latest_commit from workflow state (passed from parent)
            latest_commit = getattr(self, '_latest_commit', None)
            
            # Create Pydantic input model
            claude_input = AnalyzeWithClaudeInput(
                context_dict=PromptContextDict(**updated_context),
                config_overrides=ClaudeConfigOverrides(**config_overrides.model_dump()) if config_overrides else None,
                latest_commit=latest_commit
            )
            
            claude_result = await workflow.execute_activity(
                analyze_with_claude_context,
                args=[claude_input],
                start_to_close_timeout=timedelta(minutes=15),
                retry_policy=RetryPolicy(
                    maximum_attempts=3,
                    initial_interval=timedelta(seconds=5),
                    maximum_interval=timedelta(seconds=30),
                    backoff_coefficient=2.0
                ),
            )
            
            if claude_result.status != "success":
                raise Exception(f"Claude analysis failed for step {step_name}")
            
            # Log if result was from cache
            if claude_result.cached:
                logger.info(f"✅ Used cached result for step {step_name}: {claude_result.cache_reason or 'Unknown reason'}")
                cached_steps += 1
            
            # Get the result context with result key
            result_context = claude_result.context.model_dump()
            result_key = result_context["result_reference_key"]
            
            # Store result key for future context use
            step_results[step_name] = result_key
            all_result_info.append({
                "name": step_name,
                "description": description,
                "result_key": result_key,
                "result_length": claude_result.result_length
            })
            
            # Track the step in the results collector
            results_collector.track_step(
                step_name=step_name,
                description=description,
                result_key=result_key,
                required=is_required,
                context_dependencies=[ctx.get("val") for ctx in context_config or [] if isinstance(ctx, dict) and "val" in ctx]
            )
            
            logger.info(f"Step {step_name} completed with result key: {result_key}")
        
        # Retrieve all results from DynamoDB for final processing
        logger.info(f"Retrieving all {len(step_results)} results from DynamoDB")
        
        manager_dict = {
            "repo_name": self._repo_name,
            "step_results": step_results
        }
        
        retrieve_result = await workflow.execute_activity(
            retrieve_all_results_activity,
            args=[manager_dict],
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(
                maximum_attempts=2,
                initial_interval=timedelta(seconds=2),
                maximum_interval=timedelta(seconds=10),
            ),
        )
        
        if retrieve_result["status"] != "success":
            raise Exception("Failed to retrieve analysis results from DynamoDB")
        
        results_map = retrieve_result["results"]
        
        # Validate that all base sections are present
        is_valid, missing_sections = results_collector.validate_base_sections_present()
        if not is_valid:
            logger.warning(f"Missing base sections: {missing_sections}")
            # Log but don't fail - some repos might not have all sections
        
        # Use the collector to combine results in the correct order
        all_results = results_collector.combine_results(results_map, processing_order)
        
        # Get statistics for logging
        stats = results_collector.get_statistics()
        logger.info(f"Results collection statistics: {stats}")
        
        # Note: Cleanup is handled automatically by TTL in DynamoDB
        # We could add explicit cleanup here if needed
        
        return ProcessAnalysisResult(
            step_results=step_results,
            all_results=all_results,
            total_steps=len(step_results),
            cached_steps=cached_steps
        )

    async def _write_analysis_results(self, temp_dir: str, repo_path: str, final_analysis: str) -> WriteResultsOutput:
        """Write final analysis to file."""
        self._current_step = 8
        self._step_name = "writing_results"
        self._status = "writing_results"
        self._last_heartbeat = workflow.now()
        
        write_result = await workflow.execute_activity(
            write_analysis_result_activity,
            args=[temp_dir, repo_path, final_analysis],
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(
                maximum_attempts=2,
                initial_interval=timedelta(seconds=5),
                maximum_interval=timedelta(seconds=30),
            ),
        )
        
        # Convert dict result to Pydantic model
        return WriteResultsOutput(
            arch_file_path=write_result["arch_file_path"],
            status=write_result.get("status", "success"),
            message=write_result.get("message")
        )

    async def _save_to_hub(self, investigation_result: InvestigationResult) -> SaveToHubResult:
        """
        Save investigation results to architecture hub.
        
        Args:
            investigation_result: Dictionary containing investigation results
            
        Returns:
            SaveToHubResult with hub save status
        """
        repo_name = investigation_result.repo_name
        
        from investigator.core.config import Config
        logger.info(f"Investigation successful for {repo_name}, saving to {Config.ARCH_HUB_REPO_NAME}")
        self._status = "saving_to_hub"
        self._last_heartbeat = workflow.now()
        
        try:
            # Prepare the data for save_to_arch_hub (expects a list)
            arch_files_to_save = [{
                "repo_name": investigation_result.repo_name,
                "arch_file_content": investigation_result.arch_file_content
            }]
            
            # Save to architecture hub
            hub_result = await workflow.execute_activity(
                save_to_arch_hub,
                args=[arch_files_to_save],
                start_to_close_timeout=timedelta(minutes=10),  # Allow 10 minutes for git operations
                heartbeat_timeout=timedelta(minutes=15),
                retry_policy=RetryPolicy(
                    maximum_attempts=3,
                    initial_interval=timedelta(seconds=30),
                    maximum_interval=timedelta(minutes=2)
                ),
                task_queue="investigate-task-queue"
            )
            
            logger.info(f"Architecture hub save result for {repo_name}: {hub_result.get('message', 'Unknown')}")
            
            return SaveToHubResult(
                status=hub_result.get("status", "success"),
                message=hub_result.get("message", "Saved to architecture hub"),
                error=None
            )
            
        except Exception as e:
            logger.error(f"Failed to save {repo_name} to {Config.ARCH_HUB_REPO_NAME}: {str(e)}")
            return SaveToHubResult(
                status="failed",
                message=f"Failed to save to {Config.ARCH_HUB_REPO_NAME}: {str(e)}",
                error=str(e)
            )

    async def _save_to_dynamo(self, investigation_result: InvestigationResult, repo_name: str, repo_url: str, 
                             latest_commit: str, branch_name: str, all_results: list, 
                             arch_file_path: str, prompt_versions: Dict = None) -> SaveToDynamoResult:
        """
        Save investigation metadata to DynamoDB for future caching.
        
        Args:
            investigation_result: Current investigation results
            repo_name: Repository name
            repo_url: Repository URL  
            latest_commit: Latest commit SHA
            branch_name: Branch name
            all_results: Analysis results
            arch_file_path: Path to architecture file
            prompt_versions: Prompt versions used
            
        Returns:
            SaveToDynamoResult with metadata save status
        """
        logger.info(f"Saving investigation metadata to DynamoDB for {repo_name}")
        self._status = "saving_metadata"
        self._last_heartbeat = workflow.now()
        
        try:
            # Create Pydantic input model for save metadata
            save_metadata_input = SaveMetadataInput(
                repo_name=repo_name,
                repo_url=repo_url,
                latest_commit=latest_commit,
                branch_name=branch_name,
                analysis_summary={
                    "analysis_steps": len(all_results),
                    "prompt_versions": prompt_versions or {},
                    "arch_file_path": arch_file_path,
                    "analysis_timestamp": workflow.now().isoformat(),
                    "architecture_hub_status": investigation_result.architecture_hub.get("status", "unknown") if investigation_result.architecture_hub else "unknown"
                },
                prompt_versions=prompt_versions or {}
            )
            
            metadata_result = await workflow.execute_activity(
                save_investigation_metadata,
                args=[save_metadata_input],
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=RetryPolicy(
                    maximum_attempts=3,
                    initial_interval=timedelta(seconds=2),
                    maximum_interval=timedelta(seconds=10)
                ),
            )
            
            logger.info(f"DynamoDB metadata save result for {repo_name}: {metadata_result.message}")
            
            return SaveToDynamoResult(
                status=metadata_result.status,
                message=metadata_result.message,
                timestamp=metadata_result.timestamp,
                error=None
            )
            
        except Exception as e:
            logger.error(f"Failed to save metadata to DynamoDB for {repo_name}: {str(e)}")
            return SaveToDynamoResult(
                status="failed",
                message=f"Failed to save metadata: {str(e)}",
                timestamp=None,
                error=str(e)
            )

    @workflow.run
    async def run(self, request: InvestigateSingleRepoRequest) -> InvestigateSingleRepoResult:
        """
        Run the single repository investigation workflow.
        
        Args:
            request: InvestigateSingleRepoRequest containing investigation parameters
        
        Returns:
            InvestigateSingleRepoResult with investigation results
        """
        # Extract parameters from the request object
        repo_name = request.repo_name
        repo_url = request.repo_url
        repo_type = request.repo_type or "generic"
        force = request.force
        config_overrides = request.config_overrides or ConfigOverrides()
        
        # Initialize workflow state
        self._repo_name = repo_name
        self._status = "started"
        self._last_heartbeat = workflow.now()
        self._latest_commit = None  # Will be set after cache check
        
        logger.info(f"Starting investigation for repository: {repo_name} (type: {repo_type})")
        if force:
            logger.info(f"⚡ Force mode enabled for {repo_name} - will investigate regardless of cache")
        
        # Step 0: DynamoDB Health Check
        await self._perform_health_check()
        
        # Step 1: Clone the repository
        clone_result = await self._clone_repository(repo_url, repo_name)
        repo_path = clone_result.repo_path
        temp_dir = clone_result.temp_dir
        
        # Step 1.5: Get prompts configuration early to extract prompt versions for cache comparison
        logger.info(f"🔍 WORKFLOW: Loading prompts configuration early for cache comparison")
        early_prompts_result = await self._get_prompts_config(repo_path, repo_type, repo_url)
        prompt_versions = early_prompts_result.prompt_versions
        logger.info(f"📝 WORKFLOW: Extracted {len(prompt_versions)} prompt versions for cache check")
        
        # Step 2: Check if repository needs investigation (using DynamoDB cache)
        # Skip cache check if force is True
        cache_check_result = await self._check_cache(repo_name, repo_url, repo_path, prompt_versions)
        latest_commit = cache_check_result.latest_commit
        branch_name = cache_check_result.branch_name
        self._latest_commit = latest_commit  # Store for prompt-level caching
        
        if force:
            logger.info(f"Skipping cache check for {repo_name} due to force flag")
            needs_investigation = True
            cache_reason = "Force flag enabled"
        else:
            needs_investigation = cache_check_result.needs_investigation
            cache_reason = cache_check_result.reason
            logger.info(f"🎯 WORKFLOW: Cache check for {repo_name}: needs_investigation={needs_investigation}, reason={cache_reason}")
        # If repository doesn't need investigation, return early with cached info
        if not needs_investigation:
            logger.info(f"⏭️  WORKFLOW: Skipping investigation for {repo_name}: {cache_reason}")
            logger.info(f"🎯 FINAL DECISION: Repository {repo_name} will be SKIPPED")
            
            # Get the last investigation data if available
            last_investigation = cache_check_result.last_investigation or {}
            
            # Clean up the cloned repository since we're not investigating
            try:
                logger.info(f"Cleaning up cloned repository for skipped repo {repo_name}")
                cleanup_result = await workflow.execute_activity(
                    cleanup_repository_activity,
                    args=[repo_path, temp_dir],
                    start_to_close_timeout=timedelta(minutes=2),
                    retry_policy=RetryPolicy(
                        maximum_attempts=1,  # Don't retry cleanup failures
                        initial_interval=timedelta(seconds=1),
                    ),
                )
                logger.info(f"Cleanup result for skipped repo {repo_name}: {cleanup_result.get('message', 'Unknown')}")
            except Exception as e:
                logger.warning(f"Failed to clean up skipped repository {repo_name}: {str(e)}")
                # Don't fail the workflow due to cleanup issues
            
            return InvestigateSingleRepoResult(
                status="skipped",
                repo_name=repo_name,
                repo_url=repo_url,
                repo_type=repo_type,
                prompt_versions=prompt_versions,
                latest_commit=latest_commit,
                branch_name=branch_name,
                cached=True,
                reason=cache_reason,
                last_investigation_timestamp=last_investigation.get("analysis_timestamp"),
                message=f"Repository {repo_name} skipped: {cache_reason}"
            )
        
        # Repository needs investigation - proceed with full analysis
        logger.info(f"🚀 WORKFLOW: Proceeding with full investigation for {repo_name}")
        logger.info(f"🎯 FINAL DECISION: Repository {repo_name} will be INVESTIGATED")
        
        # Step 3: Analyze repository structure
        structure_result = await self._analyze_repository_structure(repo_path)
        repo_structure = structure_result["repo_structure"]
        
        # Step 3.5: Read and cache dependencies
        deps_result = await self._read_and_cache_dependencies(repo_path)
        deps_reference_key = deps_result.get("deps_reference_key")
        deps_formatted_content = deps_result.get("formatted_content")
        
        # Step 4: Reuse prompts configuration (already loaded for cache check)
        logger.info(f"📝 WORKFLOW: Reusing prompts configuration loaded earlier")
        prompts_result = early_prompts_result  # Reuse the configuration loaded before cache check
        prompts_dir = prompts_result.prompts_dir
        processing_order = prompts_result.processing_order
        
        # Step 5: Process each analysis step as separate activities
        analysis_result = await self._process_analysis_steps(processing_order, prompts_dir, repo_structure, config_overrides, deps_formatted_content)
        step_results = analysis_result.step_results
        all_results = analysis_result.all_results
        
        # Step 6: Combine all results into final analysis using the collector
        # The collector already validated and formatted the results
        # Load base prompts config again for the final collector
        import json
        from pathlib import Path
        try:
            base_prompts_path = Path(__file__).parent.parent / "prompts" / "base_prompts.json"
            with open(base_prompts_path, 'r') as f:
                base_prompts_config = json.load(f)
        except Exception as e:
            base_prompts_config = None
        
        results_collector_final = AnalysisResultsCollector(self._repo_name, base_prompts_config)
        final_analysis = results_collector_final.generate_final_analysis(all_results)
        
        # Step 7: Write final analysis to file
        write_result = await self._write_analysis_results(temp_dir, repo_path, final_analysis)
        arch_file_path = write_result.arch_file_path
        
        investigation_result = InvestigationResult(
            status="success",
            arch_file_path=arch_file_path,
            analysis_steps=len(all_results),
            prompt_versions=prompt_versions,
            repo_name=repo_name,
            repo_url=repo_url,
            latest_commit=latest_commit,
            branch_name=branch_name,
            arch_file_content=final_analysis,
            architecture_hub=None,  # Will be populated after hub save
            metadata_saved=None     # Will be populated after metadata save
        )
        
        # Update status after investigation
        self._last_heartbeat = workflow.now()
        self._investigation_progress = investigation_result.status
        
        # Step 8: If investigation was successful, save to architecture hub
        if investigation_result.status == "success" and investigation_result.arch_file_content:
            hub_result = await self._save_to_hub(investigation_result)
            investigation_result.architecture_hub = {
                "status": hub_result.status,
                "message": hub_result.message,
                "error": hub_result.error
            }

            # If architecture hub save failed (not skipped), fail the entire workflow
            if hub_result.status == "failed":
                error_msg = f"Architecture hub save failed: {hub_result.message}"
                logger.error(error_msg)
                raise Exception(error_msg)
            elif hub_result.status == "skipped":
                logger.info(f"Architecture hub save skipped for {repo_name}: {hub_result.message}")
        else:
            logger.info(f"Skipping architecture hub save for {repo_name} - investigation not successful or no content")
            investigation_result.architecture_hub = {
                "status": "skipped",
                "message": "Investigation not successful or no content to save"
            }
        
        # Step 9: Save investigation metadata to DynamoDB for future caching
        # This happens AFTER hub save to ensure everything is complete before marking as processed
        if investigation_result.status == "success":
            dynamo_result = await self._save_to_dynamo(
                investigation_result, repo_name, repo_url, latest_commit, 
                branch_name, all_results, arch_file_path, prompt_versions
            )
            investigation_result.metadata_saved = {
                "status": dynamo_result.status,
                "message": dynamo_result.message,
                "timestamp": dynamo_result.timestamp,
                "error": dynamo_result.error
            }
        else:
            investigation_result.metadata_saved = {
                "status": "skipped",
                "message": "Investigation not successful"
            }
        
        # Step 10: Clean up the cloned repository to save space
        cleanup = {}
        try:
            logger.info(f"Cleaning up cloned repository for {repo_name}")
            cleanup_result = await workflow.execute_activity(
                cleanup_repository_activity,
                args=[repo_path, temp_dir],
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=RetryPolicy(
                    maximum_attempts=1,  # Don't retry cleanup failures
                    initial_interval=timedelta(seconds=1),
                ),
            )
            logger.info(f"Cleanup result for {repo_name}: {cleanup_result.get('message', 'Unknown')}")
            cleanup = cleanup_result
        except Exception as e:
            logger.warning(f"Failed to clean up repository {repo_name}: {str(e)}")
            # Don't fail the workflow due to cleanup issues
            cleanup = {
                "status": "failed",
                "error": str(e),
                "message": f"Cleanup failed: {str(e)}"
            }
        
        return InvestigateSingleRepoResult(
            status=investigation_result.status,
            repo_name=repo_name,
            repo_url=repo_url,
            repo_type=repo_type,
            arch_file_path=arch_file_path,
            analysis_steps=len(all_results),
            prompt_versions=prompt_versions,
            latest_commit=latest_commit,
            branch_name=branch_name,
            cached=False,
            reason="Full investigation completed",
            arch_file_content=final_analysis,
            architecture_hub=investigation_result.architecture_hub,
            metadata_saved=investigation_result.metadata_saved,
            cleanup=cleanup,
            message=f"Repository {repo_name} investigation completed successfully"
        )