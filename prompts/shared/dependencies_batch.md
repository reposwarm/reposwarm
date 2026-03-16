version=1

# Dependency Batch Analysis

Act as a software dependency analyst. Analyze the following batch of dependency files from a software project.

For each dependency found in the provided files:
- Identify the official name (e.g. 'temporalio' becomes 'Temporal') and primary role/purpose in the project
- Note the source file where it's defined
- Classify as production or development dependency
- Cite the specific file path as the source

**Critical**: Only analyze dependencies explicitly present in the provided list. Do not assume or include any dependency not shown.

## Repository Context

This is batch {batch_index} of {total_batches} covering dependency files for this repository.
Languages in this batch: {batch_languages}

## Repository Structure (Summary)

{repo_structure}

---

## Dependencies in This Batch

**Instruction**: Analyze only the dependencies listed below.

-------- LIST START ---------
{repo_deps}
-------- LIST END ---------
