"""
Repository structure analysis for the Claude Investigator.

Primary mode: pack verbatim source excerpts into the context string sent to the model
(issue: path-only trees caused hallucinations). Path-only mode remains available via config.
"""

import os
from typing import List, Optional, Set, Tuple

from .config import Config


class RepositoryAnalyzer:
    """Handles repository structure and source bundling for analysis."""

    # Directories to always skip
    SKIP_DIRS: Set[str] = {
        ".git",
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        ".env",
        "dist",
        "build",
        "target",
        ".next",
        ".nuxt",
        "coverage",
        ".pytest_cache",
        ".mypy_cache",
        ".tox",
        "egg-info",
        ".eggs",
    }

    # Text/Blob source-like extensions to include in verbatim pass
    SOURCE_EXTENSIONS: Set[str] = {
        ".py",
        ".pyi",
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        ".mjs",
        ".cjs",
        ".go",
        ".rs",
        ".java",
        ".kt",
        ".kts",
        ".cs",
        ".php",
        ".rb",
        ".swift",
        ".scala",
        ".clj",
        ".vue",
        ".svelte",
        ".ex",
        ".exs",
        ".c",
        ".h",
        ".cc",
        ".cpp",
        ".hpp",
        ".zig",
    }

    # Basenames already covered by read_dependencies / lockfiles — skip in verbatim pass
    _SKIP_BASENAMES: Set[str] = {
        "package.json",
        "package-lock.json",
        "npm-shrinkwrap.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "requirements.txt",
        "requirements-dev.txt",
        "requirements-prod.txt",
        "Pipfile",
        "Pipfile.lock",
        "poetry.lock",
        "go.sum",
        "gopkg.lock",
        "cargo.lock",
        "gemfile.lock",
        "composer.lock",
        "pom.xml",
        "build.gradle",
        "build.gradle.kts",
        "settings.gradle",
        "settings.gradle.kts",
    }

    _HIGH_VALUE_BASENAMES: Set[str] = {
        "app.py",
        "main.py",
        "wsgi.py",
        "asgi.py",
        "manage.py",
        "server.js",
        "server.ts",
        "index.js",
        "index.ts",
        "index.jsx",
        "index.tsx",
        "application.py",
        "settings.py",
        "urls.py",
        "routing.py",
        "web.py",
        "start.py",
        "run.py",
    }

    def __init__(self, logger):
        self.logger = logger

    def get_structure(self, repo_path: str, max_depth: int = None) -> str:
        """
        Build the repository context for prompts: by default, verbatim source excerpts
        with a compact layout summary; or path-only tree if REPO_ANALYZER_CONTENT_ENABLED=0.
        """
        if not Config.REPO_ANALYZER_CONTENT_ENABLED:
            return self._get_path_only_tree(repo_path, max_depth)

        content_bundle = self._build_verbatim_source_bundle(repo_path)
        if content_bundle is not None:
            return content_bundle

        self.logger.warning(
            "Falling back to path-only tree (no eligible source files or error during read)"
        )
        return self._get_path_only_tree(repo_path, max_depth)

    def _get_path_only_tree(self, repo_path: str, max_depth: int = None) -> str:
        """Legacy: file and directory tree only (file names, no contents)."""
        if max_depth is None:
            max_depth = max(0, Config.REPO_ANALYZER_TREE_MAX_DEPTH)

        self.logger.debug("Scanning repository (path-only) in: %s (max depth: %s)", repo_path, max_depth)

        repo_name = os.path.basename(repo_path.rstrip(os.sep))

        structure = [
            f"Repository: {repo_name}",
            "=" * (len(f"Repository: {repo_name}")),
            "",
        ]

        stats = {"files": 0, "dirs": 0, "nested": 0}

        for root, dirs, files in os.walk(repo_path):
            rel_path = os.path.relpath(root, repo_path)
            if rel_path == ".":
                level = 0
            else:
                level = rel_path.count(os.sep) + 1

            indent = "  " * level
            dirs[:] = [d for d in dirs if d not in self.SKIP_DIRS and not d.endswith(".egg-info")]

            if level > 0:
                dir_name = os.path.basename(root)
                structure.append(f"{indent}{Config.DIR_ICON} {dir_name}/")
                stats["dirs"] += 1

            if level >= max_depth:
                if dirs:
                    for dir_name in sorted(dirs):
                        structure.append(f"{indent}  {Config.DIR_ICON} {dir_name}/ [NESTED]")
                        stats["nested"] += 1
                dirs[:] = []
                if files:
                    structure.append(f"{indent}  [{len(files)} files]")
            else:
                file_indent = "  " * (level + 1) if level > 0 else "  "
                for file in sorted(files):
                    structure.append(f"{file_indent}{Config.FILE_ICON} {file}")
                    stats["files"] += 1

        self.logger.debug(
            "Path-only scan for '%s': %s dirs, %s files, %s nested",
            repo_name,
            stats["dirs"],
            stats["files"],
            stats["nested"],
        )
        return "\n".join(structure)

    def _should_skip_dir(self, name: str) -> bool:
        if name in self.SKIP_DIRS or name.endswith(".egg-info"):
            return True
        if name.startswith("."):
            return name not in (".github",)  # allow .github for workflows; still skip .git above
        return False

    def _path_sort_key(self, rel_posix: str) -> Tuple[int, int, str]:
        r = rel_posix.lower()
        if "openapi" in r or "swagger" in r:
            return (0, len(r), r)
        for frag in (
            "/api/",
            "/apis/",
            "/routes/",
            "/router",
            "route.",
            "/controllers/",
            "/handlers/",
            "/endpoints/",
            "/views/",
        ):
            if frag in r:
                return (1, len(r), r)
        if "controller" in r or "handler" in r:
            return (1, len(r), r)
        base = os.path.basename(r)
        if base in self._HIGH_VALUE_BASENAMES:
            return (2, len(r), r)
        if any(
            x in r
            for x in (
                "/test/",
                "/tests/",
                "/__tests__/",
                "/e2e/",
                "/node_modules/",  # belt-and-suspenders
            )
        ) or r.startswith("test/") or r.endswith("_test.py") or r.startswith("tests/"):
            return (4, len(r), r)
        return (3, len(r), r)

    def _iter_candidate_files(self, repo_path: str) -> List[str]:
        """Return sorted relative paths (posix) to read for verbatim context."""
        repo_path = os.path.abspath(repo_path)
        candidates: List[Tuple[Tuple, str]] = []

        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if not self._should_skip_dir(d)]

            for fname in files:
                if fname.startswith(".") and fname not in (".eslintrc.cjs",):
                    continue
                if fname.lower().endswith(".min.js") or fname.lower().endswith(".min.css"):
                    continue
                fpath = os.path.join(root, fname)
                ext = os.path.splitext(fname)[1].lower()
                if ext not in self.SOURCE_EXTENSIONS:
                    continue
                if fname.lower() in {x.lower() for x in self._SKIP_BASENAMES}:
                    continue

                rel = os.path.relpath(fpath, repo_path)
                rel_posix = rel.replace(os.sep, "/")
                key = self._path_sort_key(rel_posix)
                candidates.append((key, rel_posix))

        candidates.sort(key=lambda t: t[0])
        return [p for _, p in candidates]

    def _build_verbatim_source_bundle(self, repo_path: str) -> Optional[str]:
        max_file = max(1024, Config.REPO_ANALYZER_MAX_FILE_BYTES)
        max_total = max(4096, Config.REPO_ANALYZER_MAX_TOTAL_BYTES)
        max_files = max(1, Config.REPO_ANALYZER_MAX_FILES)
        layout_depth = max(0, Config.REPO_ANALYZER_LAYOUT_MAX_DEPTH)

        rel_paths = self._iter_candidate_files(repo_path)
        if not rel_paths:
            return None

        repo_name = os.path.basename(os.path.abspath(repo_path).rstrip(os.sep))
        max_bytes = max_total

        out: List[str] = [
            f"Repository: {repo_name}",
            "=" * (len(f"Repository: {repo_name}")),
            "",
            "## How to read this block",
            "",
            "Below is **verbatim source text** from text-like files in the repository (not just paths).",
            "Manifest/lock files are omitted here when redundant with the dependency section of the prompt.",
            "Files are ordered with API-like and entrypoint paths first, then the rest. Large files are truncated per-file.",
            "",
        ]

        if layout_depth > 0:
            out.append("## Compact layout (abbreviated; full tree omitted in favor of content)")
            out.append("")
            out.append(
                self._get_path_only_tree(
                    repo_path,
                    max_depth=min(
                        layout_depth, max(0, Config.REPO_ANALYZER_TREE_MAX_DEPTH)
                    ),
                )
            )
            out.append("")

        out.append("## Verbatim source files")
        out.append("")

        repo_abs = os.path.abspath(repo_path)
        used_bytes = sum(len(s.encode("utf-8", errors="replace")) for s in out)
        included = 0
        truncated_globally = 0

        for rel in rel_paths:
            if included >= max_files or used_bytes >= max_bytes:
                truncated_globally = len(rel_paths) - included
                break
            abspath = os.path.join(repo_abs, rel.replace("/", os.sep))
            try:
                st = os.stat(abspath)
            except OSError:
                continue
            if not st.st_size or st.st_size > 20 * 1024 * 1024:
                continue

            try:
                with open(abspath, "r", encoding="utf-8", errors="replace") as fh:
                    body = fh.read(max_file)
            except OSError as e:
                self.logger.debug("Skip (unreadable) %s: %s", rel, e)
                continue
            if st.st_size > max_file:
                body = body + "\n... [truncated to {} bytes; file was larger] ...\n".format(max_file)

            rel_display = rel if rel.startswith("/") else "/" + rel
            block_lines = [f"### `{rel_display}`", "", "```", body.rstrip(), "```", ""]
            block = "\n".join(block_lines)
            block_b = block.encode("utf-8", errors="replace")
            if used_bytes + len(block_b) > max_bytes:
                truncated_globally = len(rel_paths) - included
                break

            out.append(block)
            used_bytes += len(block_b)
            included += 1
        else:
            truncated_globally = max(0, len(rel_paths) - included)

        if truncated_globally:
            out.append("---")
            out.append(
                f"*Omitted: {truncated_globally} additional candidate file(s) "
                f"after reaching the size/file budget (tune REPO_ANALYZER_* env vars).*\n"
            )

        if included == 0:
            return None
        return "\n".join(out)
