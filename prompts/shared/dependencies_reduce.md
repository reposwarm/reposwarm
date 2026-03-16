version=1

# Dependency and Architecture Analysis — Synthesis

Act as a software dependency and architecture analyst. You have been provided with dependency analyses from {total_batches} separate batches covering ALL dependency files in this repository. Your task is to synthesize these into a single, unified dependency and architecture analysis.

## Objectives

The purpose of this synthesis is to:
- Provide a complete view of the internal structure and modular composition of the project.
- Present a unified, deduplicated catalog of all external dependencies used by the project.

## Instructions

1. **Analyze Core Internal Modules/Packages**:
   - Combine findings from all batches to identify the main internal modules, packages, or significant sub-components.
   - Remove duplicates — if the same module appears in multiple batch analyses, consolidate into one entry.
   - For each internal module or package, provide a brief description of its primary responsibility.

2. **Analyze External Dependencies**:
   - Merge all external dependencies found across all batches into a single deduplicated list.
   - For each dependency, state its official name, primary role or purpose, and cite the source file(s) where it's referenced.
   - **Critical**: Only include dependencies that were explicitly found in the batch analyses. Do not assume or add any dependency not mentioned.

3. **Special Instruction**:
   - Ignore any files or directories under the `arch-docs` folder.

4. **Formatting**:
   - Use clear markdown formatting for readability.
   - Organize the output into sections with appropriate headings (e.g., "Internal Modules", "External Dependencies").

## Contextual Data

{previous_context}

---

## Repository Structure and Files

{repo_structure}

---

## Batch Analysis Results

The following contains the combined results from all {total_batches} dependency analysis batches:

{repo_deps}
