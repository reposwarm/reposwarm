from temporalio import activity
import os
import sys
import json
import asyncio
import subprocess
from typing import Optional

# Import Pydantic models for type safety
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import AnalyzeWithClaudeInput, AnalyzeWithClaudeOutput, PromptContextDict

# Add parent directory to path to import investigator
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@activity.defn
async def update_repos_list() -> dict:
    """
    Update the repos.json file by fetching repositories from GitHub or CodeCommit.
    When CODECOMMIT_ENABLED=true, lists repos from CodeCommit via boto3.
    Otherwise, runs the update_repos.py script for GitHub.

    Returns:
        Dictionary containing the update status and summary
    """
    import subprocess
    import json

    activity.logger.info("Starting repository list update")

    # Check if CodeCommit is enabled
    codecommit_enabled = os.getenv('CODECOMMIT_ENABLED', '').lower() == 'true'

    if codecommit_enabled:
        activity.logger.info("CodeCommit mode enabled, listing repositories from AWS CodeCommit")
        return await _update_repos_from_codecommit()

    gitlab_enabled = os.getenv('GITLAB_ENABLED', '').lower() == 'true'
    bitbucket_enabled = os.getenv('BITBUCKET_ENABLED', '').lower() == 'true'
    azure_devops_enabled = os.getenv('AZURE_DEVOPS_ENABLED', '').lower() == 'true'

    if gitlab_enabled:
        activity.logger.info("GitLab mode enabled, listing repositories from GitLab")
        return await _update_repos_from_gitlab()
    elif bitbucket_enabled:
        activity.logger.info("Bitbucket mode enabled, listing repositories from Bitbucket")
        return await _update_repos_from_bitbucket()
    elif azure_devops_enabled:
        activity.logger.info("Azure DevOps mode enabled, listing repositories from Azure DevOps")
        return await _update_repos_from_azure_devops()
    else:
        activity.logger.info("GitHub mode, running update_repos.py script")
        return await _update_repos_from_github()


async def _update_repos_from_github() -> dict:
    """
    Update repos.json by running the update_repos.py script for GitHub.

    Returns:
        Dictionary containing the update status and summary
    """
    import subprocess
    import json

    try:
        # Get the path to the update_repos.py script
        script_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "scripts", "update_repos.py"
        )

        activity.logger.info(f"Running update_repos.py script at: {script_path}")

        # Run the script using the same Python interpreter
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout for the update process
        )

        if result.returncode != 0:
            error_msg = f"Update repos script failed with exit code {result.returncode}. Error: {result.stderr}"
            activity.logger.error(error_msg)
            return {
                "status": "failed",
                "error": error_msg,
                "stdout": result.stdout,
                "stderr": result.stderr
            }

        # Parse the output to get summary information
        lines = result.stdout.split('\n')
        summary = {
            "status": "success",
            "message": "Repository list updated successfully from GitHub",
            "output": result.stdout
        }

        # Try to extract key metrics from output
        for line in lines:
            if "Successfully fetched" in line:
                summary["fetched_repos"] = line
            elif "repositories already in repos.json" in line:
                summary["existing_repos"] = line
            elif "repositories from skip list" in line:
                summary["skipped_repos"] = line
            elif "new active repositories to add" in line:
                summary["new_repos"] = line
            elif "Total repositories:" in line:
                summary["total_repos"] = line

        activity.logger.info(f"Update repos completed: {summary.get('total_repos', 'Unknown total')}")
        return summary

    except subprocess.TimeoutExpired:
        error_msg = "Update repos script timed out after 5 minutes"
        activity.logger.error(error_msg)
        return {"status": "failed", "error": error_msg}
    except Exception as e:
        error_msg = f"Failed to run update repos script: {str(e)}"
        activity.logger.error(error_msg)
        return {"status": "failed", "error": error_msg}


async def _update_repos_from_codecommit() -> dict:
    """
    Update repos.json by fetching repositories from AWS CodeCommit.

    Returns:
        Dictionary containing the update status and summary
    """
    import json
    from investigator.core.git_manager import GitRepositoryManager
    import logging

    try:
        # Create a logger and GitRepositoryManager
        logger = logging.getLogger("codecommit_sync")
        git_manager = GitRepositoryManager(logger)

        # List CodeCommit repositories
        result = git_manager.list_codecommit_repositories()

        if result['status'] != 'success':
            error_msg = f"Failed to list CodeCommit repositories: {result.get('message', 'Unknown error')}"
            activity.logger.error(error_msg)
            return {
                "status": "failed",
                "error": error_msg
            }

        codecommit_repos = result['repositories']
        activity.logger.info(f"Found {len(codecommit_repos)} CodeCommit repositories")

        # Load existing repos.json
        repos_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "prompts", "repos.json"
        )

        try:
            with open(repos_file, 'r') as f:
                repos_data = json.load(f)
        except FileNotFoundError:
            # Create new structure if file doesn't exist
            repos_data = {
                "default": "",
                "_comment": "CodeCommit repositories",
                "repositories": {}
            }

        existing_repos = repos_data.get("repositories", {})
        new_repos_added = 0
        skipped_existing = 0

        # Add CodeCommit repositories to repos.json
        for repo in codecommit_repos:
            repo_name = repo['name']

            # Skip if already exists
            if repo_name in existing_repos:
                skipped_existing += 1
                continue

            # Add new repository
            existing_repos[repo_name] = {
                "url": repo['clone_url_http'],
                "description": repo.get('description', 'CodeCommit repository'),
                "type": "generic"  # Default type for CodeCommit repos
            }
            new_repos_added += 1

        # Update repos.json
        repos_data['repositories'] = existing_repos

        # Write back to file
        with open(repos_file, 'w') as f:
            json.dump(repos_data, f, indent=2)

        summary = {
            "status": "success",
            "message": "Repository list updated successfully from CodeCommit",
            "region": result['region'],
            "total_codecommit_repos": len(codecommit_repos),
            "new_repos_added": new_repos_added,
            "skipped_existing": skipped_existing,
            "total_repos_in_json": len(existing_repos)
        }

        activity.logger.info(
            f"CodeCommit sync completed: {new_repos_added} new repos added, "
            f"{skipped_existing} already existed, total: {len(existing_repos)}"
        )

        return summary

    except Exception as e:
        error_msg = f"Failed to update repos from CodeCommit: {str(e)}"
        activity.logger.error(error_msg)
        return {
            "status": "failed",
            "error": error_msg
        }


async def _update_repos_from_gitlab() -> dict:
    """
    Update repos.json by fetching repositories from GitLab.

    Returns:
        Dictionary containing the update status and summary
    """
    import json
    from investigator.core.git_manager import GitRepositoryManager
    import logging

    try:
        logger = logging.getLogger("gitlab_sync")
        git_manager = GitRepositoryManager(logger)

        result = git_manager.list_gitlab_repositories()

        if result['status'] != 'success':
            error_msg = f"Failed to list GitLab repositories: {result.get('message', 'Unknown error')}"
            activity.logger.error(error_msg)
            return {
                "status": "failed",
                "error": error_msg
            }

        gitlab_repos = result['repositories']
        activity.logger.info(f"Found {len(gitlab_repos)} GitLab repositories")

        repos_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "prompts", "repos.json"
        )

        try:
            with open(repos_file, 'r') as f:
                repos_data = json.load(f)
        except FileNotFoundError:
            repos_data = {
                "default": "",
                "_comment": "GitLab repositories",
                "repositories": {}
            }

        existing_repos = repos_data.get("repositories", {})
        new_repos_added = 0
        skipped_existing = 0

        for repo in gitlab_repos:
            repo_name = repo['name']

            if repo_name in existing_repos:
                skipped_existing += 1
                continue

            existing_repos[repo_name] = {
                "url": repo['clone_url_http'],
                "description": repo.get('description', 'GitLab repository'),
                "type": "generic"
            }
            new_repos_added += 1

        repos_data['repositories'] = existing_repos

        with open(repos_file, 'w') as f:
            json.dump(repos_data, f, indent=2)

        summary = {
            "status": "success",
            "message": "Repository list updated successfully from GitLab",
            "total_gitlab_repos": len(gitlab_repos),
            "new_repos_added": new_repos_added,
            "skipped_existing": skipped_existing,
            "total_repos_in_json": len(existing_repos)
        }

        activity.logger.info(
            f"GitLab sync completed: {new_repos_added} new repos added, "
            f"{skipped_existing} already existed, total: {len(existing_repos)}"
        )

        return summary

    except Exception as e:
        error_msg = f"Failed to update repos from GitLab: {str(e)}"
        activity.logger.error(error_msg)
        return {
            "status": "failed",
            "error": error_msg
        }


async def _update_repos_from_bitbucket() -> dict:
    """
    Update repos.json by fetching repositories from Bitbucket.

    Returns:
        Dictionary containing the update status and summary
    """
    import json
    from investigator.core.git_manager import GitRepositoryManager
    import logging

    try:
        logger = logging.getLogger("bitbucket_sync")
        git_manager = GitRepositoryManager(logger)

        result = git_manager.list_bitbucket_repositories()

        if result['status'] != 'success':
            error_msg = f"Failed to list Bitbucket repositories: {result.get('message', 'Unknown error')}"
            activity.logger.error(error_msg)
            return {
                "status": "failed",
                "error": error_msg
            }

        bitbucket_repos = result['repositories']
        activity.logger.info(f"Found {len(bitbucket_repos)} Bitbucket repositories")

        repos_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "prompts", "repos.json"
        )

        try:
            with open(repos_file, 'r') as f:
                repos_data = json.load(f)
        except FileNotFoundError:
            repos_data = {
                "default": "",
                "_comment": "Bitbucket repositories",
                "repositories": {}
            }

        existing_repos = repos_data.get("repositories", {})
        new_repos_added = 0
        skipped_existing = 0

        for repo in bitbucket_repos:
            repo_name = repo['name']

            if repo_name in existing_repos:
                skipped_existing += 1
                continue

            existing_repos[repo_name] = {
                "url": repo['clone_url_http'],
                "description": repo.get('description', 'Bitbucket repository'),
                "type": "generic"
            }
            new_repos_added += 1

        repos_data['repositories'] = existing_repos

        with open(repos_file, 'w') as f:
            json.dump(repos_data, f, indent=2)

        summary = {
            "status": "success",
            "message": "Repository list updated successfully from Bitbucket",
            "total_bitbucket_repos": len(bitbucket_repos),
            "new_repos_added": new_repos_added,
            "skipped_existing": skipped_existing,
            "total_repos_in_json": len(existing_repos)
        }

        activity.logger.info(
            f"Bitbucket sync completed: {new_repos_added} new repos added, "
            f"{skipped_existing} already existed, total: {len(existing_repos)}"
        )

        return summary

    except Exception as e:
        error_msg = f"Failed to update repos from Bitbucket: {str(e)}"
        activity.logger.error(error_msg)
        return {
            "status": "failed",
            "error": error_msg
        }


async def _update_repos_from_azure_devops() -> dict:
    """
    Update repos.json by fetching repositories from Azure DevOps.

    Returns:
        Dictionary containing the update status and summary
    """
    import json
    from investigator.core.git_manager import GitRepositoryManager
    import logging

    try:
        logger = logging.getLogger("azure_devops_sync")
        git_manager = GitRepositoryManager(logger)

        result = git_manager.list_azure_devops_repositories()

        if result['status'] != 'success':
            error_msg = f"Failed to list Azure DevOps repositories: {result.get('message', 'Unknown error')}"
            activity.logger.error(error_msg)
            return {
                "status": "failed",
                "error": error_msg
            }

        azure_repos = result['repositories']
        activity.logger.info(f"Found {len(azure_repos)} Azure DevOps repositories")

        repos_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "prompts", "repos.json"
        )

        try:
            with open(repos_file, 'r') as f:
                repos_data = json.load(f)
        except FileNotFoundError:
            repos_data = {
                "default": "",
                "_comment": "Azure DevOps repositories",
                "repositories": {}
            }

        existing_repos = repos_data.get("repositories", {})
        new_repos_added = 0
        skipped_existing = 0

        for repo in azure_repos:
            repo_name = repo['name']

            if repo_name in existing_repos:
                skipped_existing += 1
                continue

            existing_repos[repo_name] = {
                "url": repo['clone_url_http'],
                "description": repo.get('description', 'Azure DevOps repository'),
                "type": "generic"
            }
            new_repos_added += 1

        repos_data['repositories'] = existing_repos

        with open(repos_file, 'w') as f:
            json.dump(repos_data, f, indent=2)

        summary = {
            "status": "success",
            "message": "Repository list updated successfully from Azure DevOps",
            "total_azure_devops_repos": len(azure_repos),
            "new_repos_added": new_repos_added,
            "skipped_existing": skipped_existing,
            "total_repos_in_json": len(existing_repos)
        }

        activity.logger.info(
            f"Azure DevOps sync completed: {new_repos_added} new repos added, "
            f"{skipped_existing} already existed, total: {len(existing_repos)}"
        )

        return summary

    except Exception as e:
        error_msg = f"Failed to update repos from Azure DevOps: {str(e)}"
        activity.logger.error(error_msg)
        return {
            "status": "failed",
            "error": error_msg
        }

@activity.defn
async def read_repos_config() -> dict:
    """
    Activity to read the repositories configuration from repos.json.
    
    Returns:
        Dictionary containing the repositories configuration
    """
    import os
    import json
    
    activity.logger.info("Reading repositories configuration")
    
    repos_file_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "prompts",
        "repos.json"
    )
    
    try:
        with open(repos_file_path, 'r') as f:
            repos_data = json.load(f)
            activity.logger.info(f"Successfully read repos.json with {len(repos_data.get('repositories', {}))} repositories")
            return repos_data
    except Exception as e:
        activity.logger.error(f"Failed to read repos.json: {str(e)}")
        return {"error": str(e), "repositories": {}}

def _read_arch_file_content(arch_file_path: str) -> str:
    """
    Read the content of the arch file.
    
    Args:
        arch_file_path: Path to the arch file
        
    Returns:
        Content of the arch file as string, or empty string if file cannot be read
    """
    try:
        if os.path.exists(arch_file_path):
            with open(arch_file_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            return ""
    except Exception as e:
        return f"Error reading arch file: {str(e)}"


async def _save_to_arch_hub_local(arch_files: list) -> dict:
    """Save architecture files to a local directory instead of git."""
    from investigator.core.config import Config

    local_path = Config.ARCH_HUB_LOCAL_PATH
    if not local_path:
        return {"status": "error", "message": "ARCH_HUB_LOCAL_PATH not set"}

    os.makedirs(local_path, exist_ok=True)

    # Determine target dir (with optional ARCH_HUB_FILES_DIR subdirectory)
    if Config.ARCH_HUB_FILES_DIR:
        target_dir = os.path.join(local_path, Config.ARCH_HUB_FILES_DIR)
        os.makedirs(target_dir, exist_ok=True)
    else:
        target_dir = local_path

    saved_files = []
    for arch_data in arch_files:
        repo_name = arch_data.get("repo_name")
        arch_content = arch_data.get("arch_file_content", "")
        if not repo_name or not arch_content:
            continue

        filename = f"{repo_name}.arch.md"
        file_path = os.path.join(target_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(arch_content)
        saved_files.append(filename)
        activity.logger.info(f"Saved architecture file locally: {file_path}")
        try:
            activity.heartbeat(f"local:saved:{filename}")
        except Exception:
            pass

    if not saved_files:
        return {"status": "completed", "message": "No architecture files to save", "files_saved": []}

    activity.logger.info(f"Saved {len(saved_files)} files to {target_dir}")
    return {
        "status": "success",
        "message": f"Saved {len(saved_files)} architecture files locally",
        "files_saved": saved_files,
        "local_path": local_path
    }


@activity.defn
async def save_to_arch_hub(arch_files: list) -> dict:
    """
    Activity that saves architecture files to the results repository.
    
    Args:
        arch_files: List of dictionaries containing repo_name and arch_file_content
    
    Returns:
        Dictionary with the result of the operation
    """
    import tempfile
    import shutil
    from datetime import datetime
    # Import here to avoid workflow sandbox issues
    from investigator.core.config import Config

    # Local file save mode — skip git entirely
    if Config.ARCH_HUB_MODE == "local":
        activity.logger.info("Using local file save mode (ARCH_HUB_MODE=local)")
        try:
            activity.heartbeat("start:save_to_arch_hub_local")
        except Exception:
            pass
        return await _save_to_arch_hub_local(arch_files)
    
    # Skip if arch-hub is not configured (still using default placeholder URL)
    if Config.ARCH_HUB_BASE_URL in ("https://github.com/your-org", ""):
        activity.logger.warning("Architecture hub not configured — skipping save. "
                              "Set up with: reposwarm config arch-hub local <path> "
                              "or: reposwarm config arch-hub github --url <url>")
        return {
            "status": "skipped",
            "message": "Architecture hub not configured (ARCH_HUB_BASE_URL is default placeholder). "
                       "Configure with: reposwarm config arch-hub local <path>",
            "files_saved": []
        }
    
    activity.logger.info(f"Starting to save architecture files to {Config.ARCH_HUB_REPO_NAME}")
    try:
        activity.heartbeat("start:save_to_arch_hub")
    except Exception:
        pass
    
    # Create a temporary directory for cloning
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # Clone the results repository using GitRepositoryManager for proper auth
            from investigator.core.git_manager import GitRepositoryManager
            
            repo_url = Config.get_arch_hub_repo_url()
            repo_dir = os.path.join(temp_dir, Config.ARCH_HUB_REPO_NAME)
            
            activity.logger.info(f"Cloning repository: {repo_url}")
            
            # Use GitRepositoryManager which handles GitHub token authentication
            git_manager = GitRepositoryManager(activity.logger)
            cloned_repo_path = git_manager.clone_or_update(repo_url, repo_dir)
            
            activity.logger.info(f"Repository cloned successfully to: {cloned_repo_path}")
            
            # Send heartbeat after cloning
            try:
                activity.heartbeat("git:cloned")
            except Exception:
                pass
            
            # Determine the target directory for architecture files
            if Config.ARCH_HUB_FILES_DIR:
                target_dir = os.path.join(repo_dir, Config.ARCH_HUB_FILES_DIR)
                # Create the directory if it doesn't exist
                os.makedirs(target_dir, exist_ok=True)
            else:
                target_dir = repo_dir
            
            # Save each architecture file
            saved_files = []
            for arch_data in arch_files:
                repo_name = arch_data.get("repo_name")
                arch_content = arch_data.get("arch_file_content", "")
                
                if not repo_name or not arch_content:
                    activity.logger.warning(f"Skipping empty architecture data for: {repo_name}")
                    continue
                
                # Create filename based on repo name
                filename = f"{repo_name}.arch.md"
                file_path = os.path.join(target_dir, filename)
                
                # Write the architecture content to file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(arch_content)
                
                # Store relative path if using subdirectory
                if Config.ARCH_HUB_FILES_DIR:
                    saved_files.append(os.path.join(Config.ARCH_HUB_FILES_DIR, filename))
                else:
                    saved_files.append(filename)
                    
                activity.logger.info(f"Saved architecture file: {saved_files[-1]}")
                try:
                    activity.heartbeat(f"saved:{filename}")
                except Exception:
                    pass
            
            if not saved_files:
                return {
                    "status": "completed",
                    "message": "No architecture files to save",
                    "files_saved": []
                }
            
            # Send heartbeat before git configuration
            try:
                activity.heartbeat("git:configuring")
            except Exception:
                pass
            
            # Configure git user (required for commits)
            git_config_success = git_manager.configure_git_user(repo_dir, Config.GIT_USER_NAME, Config.GIT_USER_EMAIL)
            if not git_config_success:
                raise Exception("Failed to configure git user")
            
            # Validate GitHub token and log user info
            token_validation = git_manager.validate_github_token()
            if token_validation["status"] == "valid":
                activity.logger.info(token_validation["message"])
                
                # Check repository permissions
                permission_check = git_manager.check_repository_permissions(repo_url)
                if permission_check["status"] == "allowed":
                    activity.logger.info(permission_check["message"])
                elif permission_check["status"] == "denied":
                    activity.logger.error(permission_check["message"])
                    activity.logger.error("The GitHub token does not have push permissions to the target repository")
                    # Get the authenticated user for better error message
                    user_info = token_validation.get("user", "unknown")
                    raise Exception(
                        f"GitHub token for user '{user_info}' does not have push permissions to "
                        f"{permission_check['owner']}/{permission_check['repo']}. "
                        f"Please ensure the token has write access to the repository or update "
                        f"the ARCH_HUB_REPO_NAME in config.py to point to a repository you can access."
                    )
                else:
                    activity.logger.warning(f"Could not verify repository permissions: {permission_check['message']}")
                    
            elif token_validation["status"] == "no_token":
                activity.logger.warning(token_validation["message"])
            else:
                activity.logger.warning(token_validation["message"])
            
            # Send heartbeat before adding files
            try:
                activity.heartbeat("git:adding_files")
            except Exception:
                pass
            
            # Add all files
            subprocess.run(
                ["git", "add", "."],
                cwd=repo_dir,
                check=True
            )
            
            # Create commit message with document names in title
            # Extract just the filenames for a cleaner commit message
            doc_names = [os.path.basename(f) for f in saved_files]
            
            # Create title with document names (limit to reasonable length)
            if len(doc_names) == 1:
                commit_title = f"Update {doc_names[0]}"
            elif len(doc_names) <= 3:
                commit_title = f"Update {', '.join(doc_names)}"
            else:
                commit_title = f"Update {len(doc_names)} architecture documents"
            
            # Add details in the body
            commit_body = f"\n\nFiles updated:\n" + "\n".join(f"- {name}" for name in doc_names)
            
            commit_message = commit_title + commit_body
            
            # Send heartbeat before committing
            try:
                activity.heartbeat("git:committing")
            except Exception:
                pass
            
            # Commit changes
            commit_result = subprocess.run(
                ["git", "commit", "-m", commit_message],
                cwd=repo_dir,
                capture_output=True,
                text=True
            )
            
            if commit_result.returncode != 0 and "nothing to commit" not in commit_result.stdout:
                raise Exception(f"Failed to commit changes: {commit_result.stderr}")
            
            # Send heartbeat before pushing
            try:
                activity.heartbeat("git:pushing")
            except Exception:
                pass
            
            # Push changes using GitRepositoryManager
            push_result = git_manager.push_with_authentication(repo_dir, "main")
            
            if push_result["status"] != "success":
                raise Exception(push_result["message"])
            
            # Send heartbeat after successful push
            try:
                activity.heartbeat("git:push_complete")
            except Exception:
                pass
            
            activity.logger.info(f"Successfully saved {len(saved_files)} architecture files to {Config.ARCH_HUB_REPO_NAME}")
            
            return {
                "status": "success",
                "message": f"Successfully saved {len(saved_files)} architecture files",
                "files_saved": saved_files,
                "repository": repo_url
            }
            
        except asyncio.CancelledError:
            activity.logger.warning(f"Save to {Config.ARCH_HUB_REPO_NAME} cancelled")
            raise
        except Exception as e:
            activity.logger.error(f"Failed to save architecture files: {str(e)}")
            # Raise exception to properly signal activity failure to Temporal
            raise Exception(f"Failed to save architecture files: {str(e)}") from e 



@activity.defn
async def save_prompt_context_activity(context_dict: dict, 
                                      prompt_content: str, 
                                      repo_structure: str,
                                      deps_formatted_content: str = None) -> dict:
    """
    Activity to save prompt data using PromptContext.
    
    Args:
        context_dict: Dictionary representation of PromptContext
        prompt_content: The prompt template content
        repo_structure: Repository structure string
        deps_formatted_content: Optional formatted dependencies content
        
    Returns:
        Updated context dictionary with data reference key
    """
    activity.logger.info(f"Saving prompt data for step: {context_dict.get('step_name')}")
    
    try:
        # Import here to avoid workflow sandbox issues
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from utils.prompt_context import create_prompt_context_from_dict
        
        # Create PromptContext from dictionary using factory
        context = create_prompt_context_from_dict(context_dict)
        
        # Check if prompt needs dependencies and replace placeholder
        if deps_formatted_content:
            # Define dependency keywords to check for
            DEPENDENCY_KEYWORDS = [
                'dependencies', 'packages', 'requirements', 'libraries',
                'npm', 'pip', 'gem', 'cargo', 'maven', 'gradle', 'nuget',
                'pyproject', 'package.json', 'gemfile', '{repo_deps}'
            ]
            
            # Check if prompt contains dependency keywords
            needs_deps = any(keyword.lower() in prompt_content.lower() for keyword in DEPENDENCY_KEYWORDS)
            
            if needs_deps:
                activity.logger.info(f"Prompt contains dependency keywords - including dependencies")
                # Replace the placeholder with formatted dependencies
                prompt_content = prompt_content.replace('{repo_deps}', deps_formatted_content)
            else:
                activity.logger.debug(f"Prompt does not contain dependency keywords - skipping dependencies")
        else:
            # Replace with "not found" message if prompt expects dependencies
            if '{repo_deps}' in prompt_content:
                activity.logger.info(f"Prompt expects dependencies but none were provided")
                prompt_content = prompt_content.replace('{repo_deps}', 'No dependency files found!')
        
        # Save the prompt data
        data_key = context.save_prompt_data(prompt_content, repo_structure)
        
        activity.logger.info(f"Successfully saved prompt data with key: {data_key}")
        
        # Return updated context as dictionary
        return {
            "status": "success",
            "context": context.to_dict()
        }
        
    except Exception as e:
        activity.logger.error(f"Failed to save prompt context: {str(e)}")
        raise Exception(f"Failed to save prompt context: {str(e)}") from e


@activity.defn
async def retrieve_all_results_activity(manager_dict: dict) -> dict:
    """
    Activity to retrieve all analysis results using PromptContextManager.
    
    Args:
        manager_dict: Dictionary containing repo_name and step_results mapping
        
    Returns:
        Dictionary with all results content
    """
    activity.logger.info(f"Retrieving all results for repo: {manager_dict.get('repo_name')}")
    
    try:
        # Import here to avoid workflow sandbox issues
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from utils.prompt_context import create_prompt_context_manager
        
        # Create manager using factory and populate with step results
        manager = create_prompt_context_manager(manager_dict['repo_name'])
        manager.step_results = manager_dict.get('step_results', {})
        
        # Retrieve all results
        results = manager.retrieve_all_results()
        
        activity.logger.info(f"Successfully retrieved {len(results)} results")
        return {
            "status": "success",
            "results": results
        }
        
    except Exception as e:
        activity.logger.error(f"Failed to retrieve analysis results: {str(e)}")
        raise Exception(f"Failed to retrieve analysis results: {str(e)}") from e


@activity.defn
async def cleanup_temporary_analysis_data_activity(reference_key: str) -> dict:
    """
    Activity to cleanup temporary analysis data from DynamoDB.
    
    Args:
        reference_key: The reference key of the data to cleanup
        
    Returns:
        Dictionary with cleanup status
    """
    activity.logger.info(f"Cleaning up temporary analysis data with key: {reference_key}")
    
    try:
        # Import here to avoid workflow sandbox issues
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from utils.dynamodb_client import get_dynamodb_client
        
        # Get DynamoDB client
        dynamodb_client = get_dynamodb_client()
        
        # Delete the temporary data
        success = dynamodb_client.delete_temporary_analysis_data(reference_key)
        
        if success:
            activity.logger.info(f"Successfully cleaned up temporary data with key: {reference_key}")
            return {"status": "success", "message": f"Cleaned up data for key: {reference_key}"}
        else:
            return {"status": "not_found", "message": f"No data found for key: {reference_key}"}
        
    except Exception as e:
        activity.logger.error(f"Failed to cleanup temporary analysis data: {str(e)}")
        # Don't raise exception for cleanup failures
        return {"status": "failed", "error": str(e)}


@activity.defn
async def analyze_with_claude_context(input_params: AnalyzeWithClaudeInput) -> AnalyzeWithClaudeOutput:
    """
    Activity to analyze repository content using Claude API with PromptContext.
    Includes prompt-level caching to avoid re-running the same analysis for unchanged commits.
    
    Args:
        input_params: AnalyzeWithClaudeInput containing context_dict, config_overrides, and latest_commit
        
    Returns:
        AnalyzeWithClaudeOutput with status, updated context, result length, and cache info
    """
    # Extract parameters from the input model
    context_dict = input_params.context_dict.model_dump()
    config_overrides = input_params.config_overrides.model_dump() if input_params.config_overrides else {}
    latest_commit = input_params.latest_commit
    
    repo_name = context_dict.get('repo_name')
    step_name = context_dict.get('step_name')
    
    activity.logger.info(f"Starting Claude analysis for step: {step_name}")
    
    try:
        # Import here to avoid workflow sandbox issues
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from utils.prompt_context import create_prompt_context_from_dict
        from investigator.core.claude_analyzer import ClaudeAnalyzer
        from investigator.core.config import Config
        from utils.dynamodb_client import get_dynamodb_client
        from activities.investigation_cache import InvestigationCache
        import logging
        
        # Check prompt-level cache if commit SHA is provided
        if latest_commit and repo_name and step_name:
            # Extract version from context
            prompt_version = context_dict.get('prompt_version', '1')
            
            activity.logger.info(f"Checking prompt cache for {repo_name}/{step_name} at commit {latest_commit[:8]} version={prompt_version}")
            activity.logger.info(f"DEBUG: Full context_dict = {context_dict}")
            
            # Check if this step should be forced (bypass cache)
            force_section = getattr(config_overrides, 'force_section', None) if config_overrides else None
            should_force_this_step = force_section and force_section == step_name
            
            if should_force_this_step:
                activity.logger.info(f"🚀 Force section enabled for {step_name} - skipping cache check")
                cache_check = {
                    "needs_analysis": True,
                    "cached_result": None,
                    "reason": f"Force section override for {step_name}"
                }
            else:
                # Get appropriate storage client and create cache instance
                if os.environ.get('PROMPT_CONTEXT_STORAGE') == 'file':
                    from utils.prompt_context import create_prompt_context_manager
                    storage_client = create_prompt_context_manager(repo_name)
                else:
                    from utils.dynamodb_client import get_dynamodb_client
                    storage_client = get_dynamodb_client()
                cache = InvestigationCache(storage_client)
                
                # Check if this prompt needs analysis for this commit AND version
                cache_check = cache.check_prompt_needs_analysis(repo_name, step_name, latest_commit, prompt_version)
            
            if cache_check["cached_result"]:
                # We have a cached result, use it
                cached_result = cache_check["cached_result"]
                activity.logger.info(
                    f"Using cached result for {repo_name}/{step_name} - {cache_check['reason']}"
                )
                
                # Use the cache key directly as the result key
                result_key = cache_check.get("cached_result_key")
                if not result_key:
                    # Generate the cache key if not provided
                    from utils.storage_keys import KeyNameCreator
                    cache_key_obj = KeyNameCreator.create_prompt_cache_key(
                        repo_name=repo_name,
                        step_name=step_name,
                        commit_sha=latest_commit,
                        prompt_version=context_dict.get('prompt_version', '1')
                    )
                    result_key = cache_key_obj.to_storage_key()
                
                activity.logger.info(f"Using cached result with key: {result_key}")
                
                # Update context with the result reference key
                context_dict_with_result = context_dict.copy()
                context_dict_with_result['result_reference_key'] = result_key
                
                # Return success with cached result
                return AnalyzeWithClaudeOutput(
                    status="success",
                    context=PromptContextDict(**context_dict_with_result),
                    result_length=len(cached_result),
                    cached=True,
                    cache_reason=cache_check["reason"]
                )
            else:
                activity.logger.info(
                    f"No cache hit for {repo_name}/{step_name} - {cache_check['reason']}"
                )
        
        # Create PromptContext from dictionary using factory
        context = create_prompt_context_from_dict(context_dict)
        
        # Get prompt data and context from DynamoDB
        activity.logger.info(f"Retrieving prompt and context data")
        data = context.get_prompt_and_context()
        
        prompt_content = data["prompt_content"]
        repo_structure = data["repo_structure"]
        context_to_use = data["context"]
        
        if not prompt_content or not repo_structure:
            raise Exception(f"Invalid data: missing prompt_content or repo_structure")
        
        activity.logger.info(f"Successfully prepared data for Claude analysis")
        
        # Create a logger for the ClaudeAnalyzer
        logger = logging.getLogger(__name__)
        
        # Initialize Claude analyzer
        use_bedrock = os.getenv('CLAUDE_PROVIDER') == 'bedrock' or os.getenv('CLAUDE_CODE_USE_BEDROCK') == '1'
        api_key = os.getenv('ANTHROPIC_API_KEY', '')
        if not api_key and not use_bedrock:
            raise Exception("Claude API key not configured. Set ANTHROPIC_API_KEY or CLAUDE_PROVIDER=bedrock.")
            
        claude_analyzer = ClaudeAnalyzer(api_key, logger)
        
        # Perform the analysis
        activity.logger.info("Calling Claude API for analysis")
        result = claude_analyzer.analyze_with_context(
            prompt_content, 
            repo_structure, 
            context_to_use,
            config_overrides=config_overrides
        )
        
        activity.logger.info(f"Claude analysis completed successfully ({len(result)} characters)")
        
        # Save the result as a cache entry (this is the ONLY save we need)
        result_key = None
        try:
            # Get version from context
            prompt_version = context_dict.get('prompt_version', '1')
            
            # Get appropriate storage client and create cache instance
            if os.environ.get('PROMPT_CONTEXT_STORAGE') == 'file':
                from utils.prompt_context import create_prompt_context_manager
                storage_client = create_prompt_context_manager(repo_name)
            else:
                from utils.dynamodb_client import get_dynamodb_client
                storage_client = get_dynamodb_client()
            cache = InvestigationCache(storage_client)
            
            # Use commit SHA if available, otherwise use a placeholder
            commit_to_use = latest_commit if latest_commit else "no-commit"
            
            # Save with cache key format (includes version and commit)
            cache_save_result = cache.save_prompt_result(
                repo_name=repo_name,
                step_name=step_name,
                commit_sha=commit_to_use,
                result_content=result,
                prompt_version=prompt_version,
                ttl_days=90
            )
            
            if cache_save_result["status"] == "success":
                # Use the cache key as the result key
                result_key = cache_save_result["cache_key"]
                activity.logger.info(
                    f"Successfully saved and cached prompt result with key: {result_key}"
                )
            else:
                # This should not happen, but log it
                activity.logger.error(
                    f"Failed to save prompt result: {cache_save_result.get('message', 'Unknown error')}"
                )
                raise Exception(f"Failed to save result: {cache_save_result.get('message')}")
        except Exception as e:
            activity.logger.error(f"Failed to save result: {str(e)}")
            raise
        
        activity.logger.info(f"Result saved with key: {result_key}")
        
        # Debug: Verify the context has the result key
        context_dict_after_save = context.to_dict()
        # Update the result reference key in the context
        context_dict_after_save['result_reference_key'] = result_key
        activity.logger.info(f"Context after save - result_reference_key: {context_dict_after_save.get('result_reference_key')}")
        
        # Return updated context
        return AnalyzeWithClaudeOutput(
            status="success",
            context=PromptContextDict(**context_dict_after_save),
            result_length=len(result),
            cached=False
        )
        
    except Exception as e:
        activity.logger.error(f"Claude analysis failed: {str(e)}")
        raise Exception(f"Failed to analyze with Claude: {str(e)}") from e


@activity.defn
async def clone_repository_activity(repo_url: str, repo_name: str) -> dict:
    """
    Activity to clone a repository and return basic info.
    
    Args:
        repo_url: Repository URL to clone
        repo_name: Name of the repository
        
    Returns:
        Dictionary with clone results including temp_dir and repo_path
    """
    activity.logger.info(f"Cloning repository: {repo_name}")
    
    try:
        # Import here to avoid workflow sandbox issues
        import sys
        import os
        import uuid
        import subprocess
        import shutil
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from investigator.core.git_manager import GitRepositoryManager
        from investigator.core.utils import Utils
        import logging
        
        logger = logging.getLogger(__name__)
        git_manager = GitRepositoryManager(logger)
        
        # Create unique directory name to prevent conflicts in parallel execution
        repo_name_from_url = Utils.extract_repo_name(repo_url)
        unique_id = str(uuid.uuid4())[:8]  # Use first 8 characters of UUID
        temp_root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "temp")
        repo_dir = os.path.join(temp_root, f"{repo_name_from_url}_{unique_id}")
        
        # Try to clone the repository with different strategies
        repo_path = None
        last_error = None
        
        # Strategy 1: Try normal clone first
        try:
            activity.logger.info(f"Attempting normal clone for {repo_name}")
            repo_path = git_manager.clone_or_update(repo_url, repo_dir)
            temp_dir = repo_dir
        except Exception as e:
            last_error = e
            activity.logger.warning(f"Normal clone failed: {str(e)}")
            
            # Check if it's a resource issue (exit code -9 or similar)
            if "exit code(-9)" in str(e) or "Killed" in str(e):
                activity.logger.info("Detected potential resource issue, trying shallow clone")
                
                # Clean up failed attempt
                if os.path.exists(repo_dir):
                    shutil.rmtree(repo_dir, ignore_errors=True)
                
                # Strategy 2: Try shallow clone with depth=1
                try:
                    activity.logger.info(f"Attempting shallow clone (depth=1) for {repo_name}")
                    repo_path = _shallow_clone_repository(repo_url, repo_dir, depth=1, logger=logger)
                    temp_dir = repo_dir
                except Exception as shallow_error:
                    activity.logger.warning(f"Shallow clone with depth=1 failed: {str(shallow_error)}")
                    
                    # Clean up failed attempt
                    if os.path.exists(repo_dir):
                        shutil.rmtree(repo_dir, ignore_errors=True)
                    
                    # Strategy 3: Try minimal clone (single branch, no tags, depth=1)
                    try:
                        activity.logger.info(f"Attempting minimal clone for {repo_name}")
                        repo_path = _minimal_clone_repository(repo_url, repo_dir, logger=logger)
                        temp_dir = repo_dir
                    except Exception as minimal_error:
                        last_error = minimal_error
                        activity.logger.error(f"All clone strategies failed for {repo_name}")
            
            # If not a resource issue, raise the original error
            if repo_path is None and last_error:
                raise last_error
        
        if repo_path is None:
            raise Exception(f"Failed to clone repository after all strategies")
        
        activity.logger.info(f"Repository cloned successfully to: {repo_path}")
        
        return {
            "status": "success",
            "repo_path": str(repo_path),
            "temp_dir": str(temp_dir),
            "repo_name": repo_name
        }
        
    except Exception as e:
        activity.logger.error(f"Failed to clone repository {repo_name}: {str(e)}")
        raise Exception(f"Failed to clone repository: {str(e)}") from e


def _shallow_clone_repository(repo_url: str, target_dir: str, depth: int = 1, logger=None) -> str:
    """
    Perform a shallow clone with specified depth to reduce memory usage.
    
    Args:
        repo_url: Repository URL to clone
        target_dir: Target directory for the clone
        depth: Clone depth (default 1 for minimal history)
        logger: Logger instance
        
    Returns:
        Path to the cloned repository
    """
    import subprocess
    import os
    
    # Ensure target directory doesn't exist
    os.makedirs(os.path.dirname(target_dir), exist_ok=True)
    
    # Add authentication to URL if needed
    auth_url = repo_url
    github_token = os.getenv('GITHUB_TOKEN')
    if github_token and 'github.com' in repo_url:
        # Insert token into URL for authentication
        if repo_url.startswith('https://'):
            auth_url = repo_url.replace('https://', f'https://{github_token}@')
    
    # Build git clone command with shallow options
    cmd = [
        'git', 'clone',
        '--depth', str(depth),
        '--single-branch',  # Only clone the default branch
        '--no-tags',  # Don't fetch tags
        auth_url,
        target_dir
    ]
    
    if logger:
        logger.info(f"Running shallow clone: depth={depth}")
    
    # Mask the token in command for logging
    log_cmd = ' '.join(cmd)
    if github_token and github_token in log_cmd:
        log_cmd = log_cmd.replace(github_token, '***HIDDEN***')
    if logger:
        logger.debug(f"Clone command: {log_cmd}")
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=600  # 10 minute timeout
    )
    
    if result.returncode != 0:
        # Sanitize error message to avoid exposing tokens
        error_msg = result.stderr
        if github_token and github_token in error_msg:
            error_msg = error_msg.replace(github_token, '***HIDDEN***')
        raise Exception(f"Shallow clone failed: {error_msg}")
    
    return target_dir


def _minimal_clone_repository(repo_url: str, target_dir: str, logger=None) -> str:
    """
    Perform a minimal clone with aggressive optimization for low memory environments.
    
    Args:
        repo_url: Repository URL to clone
        target_dir: Target directory for the clone
        logger: Logger instance
        
    Returns:
        Path to the cloned repository
    """
    import subprocess
    import os
    
    # Ensure target directory doesn't exist
    os.makedirs(os.path.dirname(target_dir), exist_ok=True)
    
    # Add authentication to URL if needed
    auth_url = repo_url
    github_token = os.getenv('GITHUB_TOKEN')
    if github_token and 'github.com' in repo_url:
        if repo_url.startswith('https://'):
            auth_url = repo_url.replace('https://', f'https://{github_token}@')
    
    # Initialize empty repository first
    os.makedirs(target_dir, exist_ok=True)
    
    if logger:
        logger.info("Performing minimal clone with aggressive optimizations")
    
    # Initialize repository
    subprocess.run(['git', 'init'], cwd=target_dir, check=True)
    
    # Add remote (don't log the URL with token)
    if logger:
        # Log sanitized URL without token
        safe_url = repo_url
        if github_token and github_token in auth_url:
            safe_url = auth_url.replace(github_token, '***HIDDEN***')
        logger.debug(f"Adding remote origin: {safe_url}")
    subprocess.run(['git', 'remote', 'add', 'origin', auth_url], cwd=target_dir, check=True)
    
    # Configure to minimize memory usage
    subprocess.run(['git', 'config', 'core.compression', '0'], cwd=target_dir, check=True)
    subprocess.run(['git', 'config', 'http.postBuffer', '524288000'], cwd=target_dir, check=True)
    subprocess.run(['git', 'config', 'pack.windowMemory', '10m'], cwd=target_dir, check=True)
    subprocess.run(['git', 'config', 'pack.packSizeLimit', '100m'], cwd=target_dir, check=True)
    
    # Fetch with minimal data
    fetch_cmd = [
        'git', 'fetch',
        '--depth=1',
        '--no-tags',
        '--filter=blob:none',  # Lazy fetch blobs
        'origin', 'HEAD'
    ]
    
    result = subprocess.run(
        fetch_cmd,
        cwd=target_dir,
        capture_output=True,
        text=True,
        timeout=600
    )
    
    if result.returncode != 0:
        # Sanitize error message to avoid exposing tokens
        error_msg = result.stderr
        if github_token and github_token in error_msg:
            error_msg = error_msg.replace(github_token, '***HIDDEN***')
        raise Exception(f"Minimal fetch failed: {error_msg}")
    
    # Checkout the fetched branch
    subprocess.run(['git', 'checkout', 'FETCH_HEAD'], cwd=target_dir, check=True)
    
    return target_dir


@activity.defn
async def analyze_repository_structure_activity(repo_path: str) -> dict:
    """
    Activity to analyze repository structure.
    
    Args:
        repo_path: Path to the cloned repository
        
    Returns:
        Dictionary with structure analysis results
    """
    activity.logger.info(f"Analyzing repository structure: {repo_path}")
    
    try:
        # Import here to avoid workflow sandbox issues
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from investigator.core.repository_analyzer import RepositoryAnalyzer
        import logging
        
        logger = logging.getLogger(__name__)
        repo_analyzer = RepositoryAnalyzer(logger)
        
        # Analyze repository structure
        repo_structure = repo_analyzer.get_structure(repo_path)
        
        activity.logger.info(f"Repository structure captured ({len(repo_structure.split(chr(10)))} lines)")
        
        return {
            "status": "success",
            "repo_structure": repo_structure
        }
        
    except Exception as e:
        activity.logger.error(f"Failed to analyze repository structure: {str(e)}")
        raise Exception(f"Failed to analyze repository structure: {str(e)}") from e


@activity.defn
async def get_prompts_config_activity(repo_path: str, repo_type: str, repo_url: str) -> dict:
    """
    Activity to get prompts configuration for a repository.
    
    Args:
        repo_path: Path to the repository
        repo_type: Repository type
        repo_url: Repository URL
        
    Returns:
        Dictionary with prompts configuration
    """
    activity.logger.info(f"Getting prompts configuration for type: {repo_type}")
    
    try:
        # Import here to avoid workflow sandbox issues
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from investigator.core.repository_type_detector import RepositoryTypeDetector
        from investigator.core.file_manager import FileManager
        import logging
        
        logger = logging.getLogger(__name__)
        type_detector = RepositoryTypeDetector(logger)
        file_manager = FileManager(logger)
        
        # Get prompts directory
        prompts_dir = type_detector.get_prompts_directory(repo_path, repo_type, repo_url)
        
        # Read prompts configuration
        prompts_config = file_manager.read_prompts_config(prompts_dir)
        processing_order = prompts_config.get("processing_order", [])
        
        # Extract prompt versions for cache comparison
        prompt_versions = {}
        activity.logger.info(f"Extracting prompt versions from {len(processing_order)} analysis steps")
        
        # Import AnalysisResultsCollector for version extraction
        from investigator.core.analysis_results_collector import AnalysisResultsCollector
        
        for step in processing_order:
            step_name = step.get("name", "unknown")
            prompt_file = step.get("file", "")
            
            if prompt_file:
                # Construct full path to prompt file
                import os
                if prompt_file.startswith("../"):
                    # Shared prompt - relative to prompts base directory
                    prompt_path = os.path.normpath(os.path.join(prompts_dir, prompt_file))
                else:
                    # Domain-specific prompt
                    prompt_path = os.path.join(prompts_dir, prompt_file)
                
                try:
                    # Read prompt content and extract version
                    with open(prompt_path, 'r', encoding='utf-8') as f:
                        prompt_content = f.read()
                    
                    version = AnalysisResultsCollector.extract_prompt_version(prompt_content)
                    prompt_versions[step_name] = version
                    activity.logger.debug(f"   {step_name}: v{version} from {prompt_file}")
                    
                except Exception as e:
                    activity.logger.warning(f"Failed to read prompt {prompt_file}: {e}")
                    prompt_versions[step_name] = "1"  # Default version
            else:
                activity.logger.warning(f"No file specified for step {step_name}")
                prompt_versions[step_name] = "1"  # Default version
        
        activity.logger.info(f"Found {len(processing_order)} analysis steps with {len(prompt_versions)} prompt versions")
        
        return {
            "status": "success",
            "prompts_dir": prompts_dir,
            "processing_order": processing_order,
            "prompt_versions": prompt_versions
        }
        
    except Exception as e:
        activity.logger.error(f"Failed to get prompts configuration: {str(e)}")
        raise Exception(f"Failed to get prompts configuration: {str(e)}") from e


@activity.defn
async def read_prompt_file_activity(prompts_dir: str, file_name: str) -> dict:
    """
    Activity to read a prompt file and extract its version.
    
    Args:
        prompts_dir: Directory containing prompts
        file_name: Name of the prompt file
        
    Returns:
        Dictionary with prompt content and version
    """
    activity.logger.info(f"Reading prompt file: {file_name}")
    
    try:
        # Import here to avoid workflow sandbox issues
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from investigator.core.file_manager import FileManager
        from investigator.core.analysis_results_collector import AnalysisResultsCollector
        import logging
        
        logger = logging.getLogger(__name__)
        file_manager = FileManager(logger)
        
        # Read the prompt file
        prompt_content = file_manager.read_prompt_file(prompts_dir, file_name)
        
        if prompt_content is None:
            return {
                "status": "not_found",
                "prompt_content": None,
                "prompt_version": "1"  # Default version for missing files
            }
        
        # Extract version from prompt content
        prompt_version = AnalysisResultsCollector.extract_prompt_version(prompt_content)
        
        activity.logger.info(f"Successfully read prompt file: {file_name} (version={prompt_version})")
        
        return {
            "status": "success",
            "prompt_content": prompt_content,
            "prompt_version": prompt_version
        }
        
    except Exception as e:
        activity.logger.error(f"Failed to read prompt file {file_name}: {str(e)}")
        raise Exception(f"Failed to read prompt file: {str(e)}") from e


@activity.defn
async def cleanup_repository_activity(repo_path: str, temp_dir: str = None) -> dict:
    """
    Activity to clean up a cloned repository from the filesystem.
    
    Args:
        repo_path: Path to the repository to clean up
        temp_dir: Optional temporary directory to clean up (if different from repo_path)
        
    Returns:
        Dictionary with cleanup results
    """
    activity.logger.info(f"Cleaning up repository at: {repo_path}")
    
    try:
        import shutil
        import os
        
        cleaned_paths = []
        
        # Clean up the repository path
        if repo_path and os.path.exists(repo_path):
            try:
                shutil.rmtree(repo_path, ignore_errors=True)
                cleaned_paths.append(repo_path)
                activity.logger.info(f"Removed repository directory: {repo_path}")
            except Exception as e:
                activity.logger.warning(f"Failed to remove repository directory {repo_path}: {str(e)}")
        
        # Clean up temp directory if it's different from repo_path
        if temp_dir and temp_dir != repo_path and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
                cleaned_paths.append(temp_dir)
                activity.logger.info(f"Removed temp directory: {temp_dir}")
            except Exception as e:
                activity.logger.warning(f"Failed to remove temp directory {temp_dir}: {str(e)}")
        
        # Also clean up any .arch.md files that might have been created in the temp directory
        if temp_dir:
            parent_dir = os.path.dirname(temp_dir)
            repo_name = os.path.basename(temp_dir).split('_')[0]  # Remove UUID suffix
            arch_file = os.path.join(parent_dir, f"{repo_name}.arch.md")
            if os.path.exists(arch_file):
                try:
                    os.remove(arch_file)
                    cleaned_paths.append(arch_file)
                    activity.logger.info(f"Removed arch file: {arch_file}")
                except Exception as e:
                    activity.logger.warning(f"Failed to remove arch file {arch_file}: {str(e)}")
        
        if cleaned_paths:
            activity.logger.info(f"Successfully cleaned up {len(cleaned_paths)} paths")
            return {
                "status": "success",
                "message": f"Cleaned up {len(cleaned_paths)} paths",
                "cleaned_paths": cleaned_paths
            }
        else:
            activity.logger.warning("No paths found to clean up")
            return {
                "status": "success",
                "message": "No paths found to clean up",
                "cleaned_paths": []
            }
        
    except Exception as e:
        activity.logger.error(f"Failed to clean up repository: {str(e)}")
        # Don't raise exception - cleanup failures shouldn't fail the workflow
        return {
            "status": "failed",
            "message": f"Cleanup failed: {str(e)}",
            "cleaned_paths": []
        }


@activity.defn
async def write_analysis_result_activity(temp_dir: str, repo_path: str, final_analysis: str) -> dict:
    """
    Activity to write the final analysis result to file.
    
    Args:
        temp_dir: Temporary directory
        repo_path: Repository path
        final_analysis: Final analysis content
        
    Returns:
        Dictionary with write results
    """
    activity.logger.info("Writing final analysis to file")
    
    try:
        # Import here to avoid workflow sandbox issues
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from investigator.core.file_manager import FileManager
        import logging
        
        logger = logging.getLogger(__name__)
        file_manager = FileManager(logger)
        
        # Write final analysis to file
        arch_file_path = file_manager.write_analysis(repo_path, final_analysis)
        
        activity.logger.info(f"Analysis written to: {arch_file_path}")
        
        return {
            "status": "success",
            "arch_file_path": arch_file_path
        }
        
    except Exception as e:
        activity.logger.error(f"Failed to write analysis result: {str(e)}")
        raise Exception(f"Failed to write analysis result: {str(e)}") from e


@activity.defn
async def read_dependencies_activity(repo_path: str) -> dict:
    """
    Activity to read and format all dependency files from a repository.
    
    Args:
        repo_path: Path to the cloned repository
        
    Returns:
        Dictionary with formatted dependency content ready for prompt inclusion
    """
    activity.logger.info(f"Reading dependency files from: {repo_path}")
    
    try:
        import os
        import glob
        import json
        from pathlib import Path
        
        # Define dependency file patterns
        DEPENDENCY_PATTERNS = {
            "Python": {
                "production": [
                    "requirements.txt", "requirements-prod.txt", "requirements-production.txt",
                    "pyproject.toml", "setup.py", "setup.cfg",
                    "Pipfile", "environment.yml", "environment.yaml",
                    "conda.yml", "conda.yaml"
                ],
                "dev": [
                    "requirements-dev.txt", "requirements-test.txt",
                    "requirements-development.txt", "test-requirements.txt",
                    "dev-requirements.txt"
                ],
                "exclude": ["Pipfile.lock", "poetry.lock"]
            },
            "JavaScript": {
                "production": ["package.json", "bower.json", "lerna.json"],
                "dev": [],  # package.json contains both
                "exclude": ["package-lock.json", "yarn.lock", "pnpm-lock.yaml", "node_modules"]
            },
            "Ruby": {
                "production": ["Gemfile", "*.gemspec"],
                "dev": [],  # Gemfile contains both
                "exclude": ["Gemfile.lock"]
            },
            "Go": {
                "production": ["go.mod", "Gopkg.toml"],
                "dev": [],
                "exclude": ["go.sum", "Gopkg.lock"]
            },
            "Rust": {
                "production": ["Cargo.toml"],
                "dev": [],
                "exclude": ["Cargo.lock"]
            },
            "Java": {
                "production": ["pom.xml", "build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts"],
                "dev": [],
                "exclude": []
            },
            "CSharp": {
                "production": ["*.csproj", "*.fsproj", "*.vbproj", "packages.config", "Directory.Build.props"],
                "dev": [],
                "exclude": ["packages.lock.json"]
            },
            "PHP": {
                "production": ["composer.json"],
                "dev": [],
                "exclude": ["composer.lock"]
            },
            "Other": {
                "production": ["Dockerfile", "docker-compose.yml", "docker-compose.yaml", ".tool-versions"],
                "dev": [],
                "exclude": []
            }
        }
        
        repo_path_obj = Path(repo_path)
        dependencies_by_language = {}
        
        # Search for dependency files
        for language, patterns in DEPENDENCY_PATTERNS.items():
            production_deps = []
            dev_deps = []
            
            # Search for production dependency files
            for pattern in patterns["production"]:
                found_files = list(repo_path_obj.rglob(pattern))
                for file_path in found_files:
                    # Skip excluded files
                    if any(exclude in file_path.name for exclude in patterns["exclude"]):
                        continue
                    
                    # Read file content
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # Get relative path from repo root
                        relative_path = "/" + str(file_path.relative_to(repo_path_obj))
                        
                        # For JavaScript, parse package.json to separate prod and dev deps
                        if language == "JavaScript" and file_path.name == "package.json":
                            try:
                                package_data = json.loads(content)
                                
                                # Create separate content for production dependencies
                                prod_content = _extract_package_json_section(content, ["dependencies", "peerDependencies"])
                                if prod_content.strip():
                                    production_deps.append({
                                        "full_path": relative_path,
                                        "content": prod_content
                                    })
                                
                                # Create separate content for dev dependencies
                                dev_content = _extract_package_json_section(content, ["devDependencies"])
                                if dev_content.strip():
                                    dev_deps.append({
                                        "full_path": relative_path + " (dev)",
                                        "content": dev_content
                                    })
                                
                            except json.JSONDecodeError:
                                # If JSON parsing fails, treat as production
                                production_deps.append({
                                    "full_path": relative_path,
                                    "content": content
                                })
                        
                        # For Ruby Gemfile, parse groups
                        elif language == "Ruby" and file_path.name == "Gemfile":
                            prod_content, dev_content = _parse_gemfile_groups(content)
                            
                            if prod_content.strip():
                                production_deps.append({
                                    "full_path": relative_path,
                                    "content": prod_content
                                })
                            
                            if dev_content.strip():
                                dev_deps.append({
                                    "full_path": relative_path + " (dev/test)",
                                    "content": dev_content
                                })
                        
                        # For Python pyproject.toml, parse sections
                        elif language == "Python" and file_path.name == "pyproject.toml":
                            prod_content, dev_content = _parse_pyproject_dependencies(content)
                            
                            if prod_content.strip():
                                production_deps.append({
                                    "full_path": relative_path,
                                    "content": prod_content
                                })
                            
                            if dev_content.strip():
                                dev_deps.append({
                                    "full_path": relative_path + " (dev)",
                                    "content": dev_content
                                })
                        
                        else:
                            # Default: treat as production dependency
                            production_deps.append({
                                "full_path": relative_path,
                                "content": content
                            })
                            
                    except Exception as e:
                        activity.logger.warning(f"Failed to read dependency file {file_path}: {e}")
                        continue
            
            # Search for dev dependency files
            for pattern in patterns["dev"]:
                found_files = list(repo_path_obj.rglob(pattern))
                for file_path in found_files:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        relative_path = "/" + str(file_path.relative_to(repo_path_obj))
                        dev_deps.append({
                            "full_path": relative_path,
                            "content": content
                        })
                        
                    except Exception as e:
                        activity.logger.warning(f"Failed to read dev dependency file {file_path}: {e}")
                        continue
            
            # Only add language if we found files
            if production_deps or dev_deps:
                dependencies_by_language[language] = {
                    "production_dependencies": production_deps,
                    "developer_only_dependencies": dev_deps
                }
        
        # Format dependencies for prompts
        formatted_content = _format_dependencies_for_prompt(dependencies_by_language)
        
        total_files = sum(
            len(lang_deps["production_dependencies"]) + len(lang_deps["developer_only_dependencies"])
            for lang_deps in dependencies_by_language.values()
        )
        
        if total_files == 0:
            message = "No dependency files found!"
            activity.logger.info(message)
        else:
            message = f"Found dependency files in {len(dependencies_by_language)} languages ({total_files} files total)"
            activity.logger.info(message)
        
        return {
            "status": "success",
            "formatted_content": formatted_content,
            "raw_dependencies": dependencies_by_language,
            "message": message
        }
        
    except Exception as e:
        activity.logger.error(f"Failed to read dependencies: {str(e)}")
        return {
            "status": "error",
            "formatted_content": "Error reading dependency files!",
            "raw_dependencies": {},
            "message": f"Error: {str(e)}"
        }


def _format_dependencies_for_prompt(dependencies: dict) -> str:
    """Format dependencies for inclusion in prompts."""
    if not dependencies:
        return "No dependency files found!"
    
    output = []
    output.append("## Dependencies\n")
    
    # Sort languages alphabetically
    for language in sorted(dependencies.keys()):
        lang_deps = dependencies[language]
        output.append(f"### {language}\n")
        
        # Production dependencies first
        if lang_deps.get("production_dependencies"):
            output.append("#### Production Dependencies\n")
            # Sort by path for consistency
            sorted_prod = sorted(lang_deps["production_dependencies"], key=lambda x: x["full_path"])
            for dep_file in sorted_prod:
                output.append(f"**File:** `{dep_file['full_path']}`\n")
                output.append("```")
                output.append(dep_file['content'])
                output.append("```\n")
        
        # Developer dependencies second
        if lang_deps.get("developer_only_dependencies"):
            output.append("#### Developer-Only Dependencies\n")
            # Sort by path for consistency
            sorted_dev = sorted(lang_deps["developer_only_dependencies"], key=lambda x: x["full_path"])
            for dep_file in sorted_dev:
                output.append(f"**File:** `{dep_file['full_path']}`\n")
                output.append("```")
                output.append(dep_file['content'])
                output.append("```\n")
    
    return "\n".join(output)


def _extract_package_json_section(content: str, sections: list) -> str:
    """Extract specific sections from package.json content."""
    try:
        import json
        package_data = json.loads(content)
        extracted = {}
        
        for section in sections:
            if section in package_data and package_data[section]:
                extracted[section] = package_data[section]
        
        if extracted:
            return json.dumps(extracted, indent=2)
        return ""
    except:
        return ""


def _parse_gemfile_groups(content: str) -> tuple:
    """Parse Gemfile content to separate production and dev dependencies."""
    lines = content.split('\n')
    prod_lines = []
    dev_lines = []
    current_group = "production"
    
    for line in lines:
        stripped = line.strip()
        
        # Check for group declarations
        if stripped.startswith('group '):
            if ':development' in stripped or ':test' in stripped:
                current_group = "development"
            else:
                current_group = "production"
        elif stripped.startswith('end') and current_group != "production":
            current_group = "production"
        else:
            # Add line to appropriate group
            if current_group == "development":
                dev_lines.append(line)
            else:
                prod_lines.append(line)
    
    return '\n'.join(prod_lines), '\n'.join(dev_lines)


def _parse_pyproject_dependencies(content: str) -> tuple:
    """Parse pyproject.toml to separate production and dev dependencies."""
    try:
        import toml
        data = toml.loads(content)
        
        prod_content = ""
        dev_content = ""
        
        # Extract production dependencies
        if 'project' in data and 'dependencies' in data['project']:
            prod_deps = {"dependencies": data['project']['dependencies']}
            prod_content = toml.dumps(prod_deps)
        
        # Extract dev dependencies (poetry style)
        if 'tool' in data and 'poetry' in data['tool'] and 'dev-dependencies' in data['tool']['poetry']:
            dev_deps = {"dev-dependencies": data['tool']['poetry']['dev-dependencies']}
            dev_content = toml.dumps(dev_deps)
        
        # Extract dev dependencies (PEP 621 style)
        if 'project' in data and 'optional-dependencies' in data['project']:
            opt_deps = {"optional-dependencies": data['project']['optional-dependencies']}
            if dev_content:
                dev_content += "\n" + toml.dumps(opt_deps)
            else:
                dev_content = toml.dumps(opt_deps)
        
        return prod_content, dev_content
    
    except ImportError:
        # If toml module not available, return original content as production
        return content, ""
    except Exception:
        # If parsing fails, return original content as production
        return content, ""


@activity.defn
async def cache_dependencies_activity(repo_name: str, dependencies_data: dict) -> dict:
    """
    Cache dependencies data using the abstracted storage layer.
    
    Args:
        repo_name: Repository name
        dependencies_data: Dependencies data from read_dependencies_activity
        
    Returns:
        dict with deps_reference_key
    """
    activity.logger.info(f"Caching dependencies for repository: {repo_name}")
    
    try:
        import os
        import sys
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # Use the abstracted storage (file or DynamoDB based on env)
        if os.environ.get('PROMPT_CONTEXT_STORAGE') == 'file':
            from utils.prompt_context import create_prompt_context_manager
            storage_client = create_prompt_context_manager(repo_name)
        else:
            from utils.dynamodb_client import get_dynamodb_client
            storage_client = get_dynamodb_client()
        
        from activities.investigation_cache import InvestigationCache
        from utils.storage_keys import KeyNameCreator
        
        # Create cache instance
        cache = InvestigationCache(storage_client)
        
        # Generate a unique key for dependencies
        deps_key = KeyNameCreator.create_dependencies_key(repo_name)
        reference_key = deps_key.to_storage_key()
        
        # Save using the abstracted method
        result = cache.save_dependencies(
            repo_name=repo_name,
            dependencies_data=dependencies_data,
            reference_key=reference_key
        )
        
        if result["status"] == "success":
            activity.logger.info(f"Successfully cached dependencies for {repo_name}")
            return {
                "status": "success",
                "deps_reference_key": result["reference_key"]
            }
        else:
            activity.logger.error(f"Failed to cache dependencies: {result.get('error', 'Unknown error')}")
            return {
                "status": "failed",
                "deps_reference_key": None,
                "error": result.get("error", "Unknown error")
            }
        
    except Exception as e:
        activity.logger.error(f"Failed to cache dependencies for {repo_name}: {str(e)}")
        return {
            "status": "failed",
            "deps_reference_key": None,
            "error": str(e)
        } 