version=2

You are a software architect who is an experts with feature flag systems , CI-CD and things related to them. Analyze all feature flag implementations and usage in this codebase.

**Special Instruction**: If no feature flag systems are found, return "no feature flag usage detected". Only document feature flag systems that are ACTUALLY implemented in the codebase. Do NOT list feature flag platforms or tools that are not present.

## Feature Flag Framework Detection

Identify any feature flag platforms or libraries in use:

**Commercial Platforms:**

- Flagsmith, LaunchDarkly, Split.io, Optimizely, ConfigCat, Unleash

**Open Source/Custom:**

- Unleash (self-hosted), custom database flags, environment variables

**SDKs/Libraries:**

- Look for packages like: `launchdarkly-*`, `flagsmith-*`, `@splitsoftware/*`, `@unleash/*`, `configcat-*`, etc.

## Feature Flag Inventory

For each flag found, document:

### Flag: `flag_name`

**Type:** [Boolean/String/Number/JSON]

**Purpose:** [Brief description]

**Default Value:** [Default state]

**Used In:**

- File: `path/to/file.ext` (lines X-Y)
- Component/Function: [where it's evaluated]
- How would turning the flag on and off  affect the application (look closely at related methods, funxtions and classes)

**Evaluation Pattern:**

```[language]
// Show actual code snippet
```

## Framework Configuration

**Platform Used:** [Name of platform/library]

**Configuration:**

- API keys/tokens: [how managed]
- Environment setup: [dev/staging/prod differences]
- Client initialization: [file location]

## Flag Usage Patterns

**Common Patterns:**

- Simple boolean checks: `if (flag.enabled)`
- String variations: `flag.getValue('theme')`
- User targeting: `flag.isEnabledForUser(user)`

**Context Used:**

- User attributes: [ID, email, plan, etc.]
- Custom attributes: [device, location, etc.]

## Flag Categories

Group flags by purpose:

**Release Flags:** [List flags used for gradual rollouts]

**Kill Switches:** [List flags for emergency disabling]

**A/B Tests:** [List experimental flags]

**Configuration:** [List flags controlling behavior/settings]

Format the output clearly using markdown

{previous_context}

---

## Repository Structure and Files

{repo_structure}

---

## Dependencies

{repo_deps}
