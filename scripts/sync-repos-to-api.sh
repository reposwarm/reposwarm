#!/usr/bin/env bash
# Syncs repos.json into the reposwarm API server.
# Adds any repos not already registered (they are enabled by default on add).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPOS_JSON="${1:-$SCRIPT_DIR/../prompts/repos.json}"

if [[ ! -f "$REPOS_JSON" ]]; then
  echo "Error: $REPOS_JSON not found" >&2
  exit 1
fi

if ! command -v reposwarm &>/dev/null; then
  echo "Error: reposwarm CLI not found in PATH" >&2
  exit 1
fi

if ! command -v jq &>/dev/null; then
  echo "Error: jq is required but not found" >&2
  exit 1
fi

# Get repos already registered in the API
existing=$(reposwarm repos list --json --for-agent 2>/dev/null | jq -r '.[].name // empty' 2>/dev/null || true)

# Read repo names from repos.json
names=$(jq -r '.repositories | keys[]' "$REPOS_JSON")

added=0
skipped=0
failed=0

for name in $names; do
  url=$(jq -r --arg n "$name" '.repositories[$n].url' "$REPOS_JSON")

  # Determine source from URL
  if [[ "$url" == *github.com* ]]; then
    source="GitHub"
  else
    source="CodeCommit"
  fi

  # Add if not already registered
  if echo "$existing" | grep -qx "$name"; then
    echo "  skip  $name (already registered)"
    ((skipped++))
  else
    if reposwarm repos add "$name" --url "$url" --source "$source" --for-agent 2>&1; then
      echo "  added $name"
      ((added++))
    else
      echo "  FAIL  $name — could not add" >&2
      ((failed++))
    fi
  fi
done

echo ""
echo "Done: $added added, $skipped skipped, $failed failed"
