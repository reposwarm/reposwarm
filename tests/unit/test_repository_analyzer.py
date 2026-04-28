"""Tests for RepositoryAnalyzer verbatim source bundling."""

import logging
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from investigator.core.config import Config
from investigator.core.repository_analyzer import RepositoryAnalyzer


@pytest.fixture
def log():
    return logging.getLogger("test.repository_analyzer")


def test_get_structure_includes_verbatim_source(tmp_path, log):
    (tmp_path / "api").mkdir()
    (tmp_path / "api" / "main.py").write_text("def app():\n    return 'x'\n", encoding="utf-8")
    (tmp_path / "other.py").write_text("# other\n", encoding="utf-8")

    a = RepositoryAnalyzer(log)
    with patch.object(Config, "REPO_ANALYZER_CONTENT_ENABLED", True):
        with patch.object(Config, "REPO_ANALYZER_MAX_TOTAL_BYTES", 500_000):
            with patch.object(Config, "REPO_ANALYZER_LAYOUT_MAX_DEPTH", 0):
                s = a.get_structure(str(tmp_path))
    assert "Verbatim source files" in s
    assert "def app():" in s
    assert "/api/main.py" in s or "api/main.py" in s


def test_get_structure_path_only_when_disabled(tmp_path, log):
    (tmp_path / "a.py").write_text("SECRET", encoding="utf-8")
    a = RepositoryAnalyzer(log)
    with patch.object(Config, "REPO_ANALYZER_CONTENT_ENABLED", False):
        s = a.get_structure(str(tmp_path))
    assert "SECRET" not in s
    assert "a.py" in s
    assert Config.FILE_ICON in s or "a.py" in s


def test_skips_lockfiles_in_verbatim_pass(tmp_path, log):
    (tmp_path / "package-lock.json").write_text('{"n":1}', encoding="utf-8")
    (tmp_path / "x.py").write_text("a = 1", encoding="utf-8")
    a = RepositoryAnalyzer(log)
    with patch.object(Config, "REPO_ANALYZER_CONTENT_ENABLED", True):
        with patch.object(Config, "REPO_ANALYZER_LAYOUT_MAX_DEPTH", 0):
            s = a.get_structure(str(tmp_path))
    assert "a = 1" in s
    assert '"n":1' not in s
