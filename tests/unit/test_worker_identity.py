"""
Tests for worker identity uniqueness when scaling.

Verifies that each worker gets a unique identity by default (hostname + PID),
enabling docker compose --scale worker=N to create distinguishable workers
in Temporal's worker list.
"""

import os
import sys
import socket
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))


def _get_temporal_config():
    """Import get_temporal_config with mocked temporalio to avoid import errors."""
    # The investigate_worker module imports temporalio at module level.
    # Mock it to avoid needing the full temporalio package in unit tests.
    import importlib
    from unittest.mock import MagicMock

    # Ensure temporalio modules are mocked if not available
    temporalio_mocks = {}
    modules_to_mock = [
        'temporalio', 'temporalio.worker', 'temporalio.client',
        'temporalio.contrib', 'temporalio.contrib.pydantic',
        'temporalio.contrib.pydantic.pydantic_data_converter',
        'temporalio.common', 'temporalio.exceptions',
    ]
    for mod in modules_to_mock:
        if mod not in sys.modules:
            temporalio_mocks[mod] = MagicMock()
            sys.modules[mod] = temporalio_mocks[mod]

    try:
        # Force reimport to pick up env changes
        if 'investigate_worker' in sys.modules:
            importlib.reload(sys.modules['investigate_worker'])
        from investigate_worker import get_temporal_config
        return get_temporal_config()
    finally:
        # Clean up mocks
        for mod in temporalio_mocks:
            if sys.modules.get(mod) is temporalio_mocks[mod]:
                del sys.modules[mod]


class TestWorkerIdentity:
    """Tests for unique worker identity generation."""

    def test_default_identity_includes_hostname(self):
        """Default worker identity should include the hostname."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('TEMPORAL_IDENTITY', None)
            config = _get_temporal_config()

        hostname = socket.gethostname()
        assert hostname in config['identity'], (
            f"Expected hostname '{hostname}' in identity '{config['identity']}'. "
            "Without unique identity, scaled workers are indistinguishable in Temporal."
        )

    def test_default_identity_includes_pid(self):
        """Default worker identity should include the PID."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('TEMPORAL_IDENTITY', None)
            config = _get_temporal_config()

        pid = str(os.getpid())
        assert pid in config['identity'], (
            f"Expected PID '{pid}' in identity '{config['identity']}'. "
            "PID ensures uniqueness even on the same host."
        )

    def test_default_identity_starts_with_prefix(self):
        """Default identity should start with 'investigate-worker-'."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('TEMPORAL_IDENTITY', None)
            config = _get_temporal_config()

        assert config['identity'].startswith('investigate-worker-'), (
            f"Expected identity to start with 'investigate-worker-', got '{config['identity']}'"
        )

    def test_explicit_identity_overrides_default(self):
        """TEMPORAL_IDENTITY env var should override the generated default."""
        with patch.dict(os.environ, {'TEMPORAL_IDENTITY': 'my-custom-worker'}):
            config = _get_temporal_config()

        assert config['identity'] == 'my-custom-worker', (
            f"Expected 'my-custom-worker', got '{config['identity']}'. "
            "Explicit TEMPORAL_IDENTITY should take priority."
        )
