#!/usr/bin/env python3
"""
Example script demonstrating how to use OpenCode Investigator with private GitHub repositories.

Supports multiple AI providers: Anthropic, OpenAI, Google, and more.
"""

import os
import sys
import asyncio
from investigator import OpenCodeInvestigator, investigate_repo


def main():
    """Example usage of OpenCode Investigator with private repositories."""

    # Check provider configuration
    provider_id = os.getenv('PROVIDER_ID', 'anthropic')
    print(f"Using AI provider: {provider_id}")

    # Check for appropriate API key based on provider
    if provider_id == 'anthropic' and not os.getenv('ANTHROPIC_API_KEY'):
        print("Error: ANTHROPIC_API_KEY environment variable is required for Anthropic provider")
        print("Set it with: export ANTHROPIC_API_KEY='your-api-key'")
        sys.exit(1)
    elif provider_id == 'openai' and not os.getenv('OPENAI_API_KEY'):
        print("Error: OPENAI_API_KEY environment variable is required for OpenAI provider")
        print("Set it with: export OPENAI_API_KEY='your-api-key'")
        sys.exit(1)
    elif provider_id == 'google' and not os.getenv('GOOGLE_API_KEY'):
        print("Error: GOOGLE_API_KEY environment variable is required for Google provider")
        print("Set it with: export GOOGLE_API_KEY='your-api-key'")
        sys.exit(1)

    # Check if GitHub token is available
    github_token = os.getenv('GITHUB_TOKEN')
    if github_token:
        print("GitHub token found - private repositories can be accessed")
    else:
        print("No GitHub token found - only public repositories can be accessed")
        print("   To access private repos, set: export GITHUB_TOKEN='your-github-token'")

    # Example 1: Using the convenience function
    print("\n--- Example 1: Using convenience function ---")

    # Replace with your repository URL
    repo_url = "https://github.com/username/repository"

    if len(sys.argv) > 1:
        repo_url = sys.argv[1]
    else:
        print(f"No repository URL provided, using example: {repo_url}")
        print("Usage: python example_private_repo.py <repository-url>")

    try:
        print(f"\nAnalyzing repository: {repo_url}")
        arch_file = asyncio.run(investigate_repo(repo_url, log_level="INFO"))
        print(f"Analysis complete! Results saved to: {arch_file}")
    except Exception as e:
        print(f"Error: {e}")
        if "Authentication failed" in str(e) and github_token:
            print("\nTroubleshooting tips:")
            print("1. Ensure your GitHub token has 'repo' scope permissions")
            print("2. Check that the token hasn't expired")
            print("3. Verify the repository URL is correct")
        elif "Authentication failed" in str(e):
            print("\nThis might be a private repository. To access it:")
            print("1. Create a GitHub personal access token with 'repo' scope")
            print("2. Set the environment variable: export GITHUB_TOKEN='your-token'")
        sys.exit(1)

    # Example 2: Using the class directly with custom configuration
    print("\n--- Example 2: Using OpenCodeInvestigator class ---")

    try:
        # Create investigator with DEBUG logging for more details
        investigator = OpenCodeInvestigator(provider_id=provider_id, log_level="DEBUG")

        # You can also pass a different repo here
        # arch_file = asyncio.run(investigator.investigate_repository("https://github.com/another/repo"))

        print("Investigator instance created successfully")

    except Exception as e:
        print(f"Error creating investigator: {e}")
        sys.exit(1)

    print("\n--- Additional Information ---")
    print("\nTo create a GitHub personal access token:")
    print("1. Go to https://github.com/settings/tokens")
    print("2. Click 'Generate new token' (classic)")
    print("3. Give it a descriptive name")
    print("4. Select the 'repo' scope for full repository access")
    print("5. Click 'Generate token' and copy it")
    print("6. Set it as environment variable: export GITHUB_TOKEN='ghp_...'")

    print("\nSupported repository formats:")
    print("- https://github.com/owner/repo")
    print("- https://github.com/owner/repo.git")
    print("- git@github.com:owner/repo.git (SSH URLs)")
    print("- Local file paths to repositories")

    print("\nSupported AI providers:")
    print("- anthropic (default)")
    print("- openai")
    print("- google")
    print("- bedrock")
    print("- azure")
    print("- ollama")


# Backwards compatibility alias
ClaudeInvestigator = OpenCodeInvestigator


if __name__ == "__main__":
    main()
