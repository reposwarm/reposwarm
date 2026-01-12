#!/usr/bin/env python3
"""
Example usage of the OpenCode Investigator.

This script demonstrates how to use the OpenCodeInvestigator class to analyze
repository structure and generate architecture documentation.

Supports multiple AI providers: Anthropic, OpenAI, Google, and more.
"""

import os
import asyncio
from investigator import OpenCodeInvestigator, investigate_repo


def main():
    """Example usage of the OpenCode Investigator."""

    # Example 1: Using the convenience function with default logging
    print("=== Example 1: Using convenience function (INFO logging) ===")
    try:
        # Replace with an actual repository URL
        repo_url = "https://github.com/example/repo"

        # Uses PROVIDER_ID env var (default: anthropic)
        # Ensure appropriate API key is set (ANTHROPIC_API_KEY, OPENAI_API_KEY, etc.)
        arch_file_path = asyncio.run(investigate_repo(repo_url))
        print(f"Analysis completed! Check: {arch_file_path}")

    except Exception as e:
        print(f"Error: {e}")

    print("\n" + "="*50 + "\n")

    # Example 2: Using the class directly with DEBUG logging
    print("=== Example 2: Using OpenCodeInvestigator class (DEBUG logging) ===")
    try:
        # You can specify the provider directly
        # Options: anthropic (default), openai, google, bedrock, azure, ollama
        investigator = OpenCodeInvestigator(provider_id="anthropic", log_level="DEBUG")

        # Replace with an actual repository URL
        repo_url = "https://github.com/example/repo"

        arch_file_path = asyncio.run(investigator.investigate_repository(repo_url))
        print(f"Analysis completed! Check: {arch_file_path}")

    except Exception as e:
        print(f"Error: {e}")

    print("\n" + "="*50 + "\n")

    # Example 3: Using a different provider
    print("=== Example 3: Using OpenAI provider ===")
    try:
        # Ensure OPENAI_API_KEY is set for this example
        if not os.getenv('OPENAI_API_KEY'):
            print("Skipping: OPENAI_API_KEY not set")
        else:
            investigator = OpenCodeInvestigator(provider_id="openai", log_level="INFO")

            repo_url = "https://github.com/example/repo"

            arch_file_path = asyncio.run(investigator.investigate_repository(repo_url))
            print(f"Analysis completed! Check: {arch_file_path}")

    except Exception as e:
        print(f"Error: {e}")


# Backwards compatibility alias
ClaudeInvestigator = OpenCodeInvestigator


if __name__ == "__main__":
    main()
