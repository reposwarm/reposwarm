"""
OpenCode server lifecycle manager for on-demand server spawning.
"""

import subprocess
import time
import atexit
import shutil
from typing import Optional
from opencode_ai import Opencode


class OpenCodeServerManager:
    """Manages on-demand OpenCode server lifecycle."""

    def __init__(self, port: int = 4096, logger=None):
        """
        Initialize the server manager.

        Args:
            port: Port to run the OpenCode server on
            logger: Optional logger instance
        """
        self.port = port
        self.process: Optional[subprocess.Popen] = None
        self.logger = logger
        self._base_url = f"http://127.0.0.1:{port}"
        self._cleanup_registered = False

    @property
    def base_url(self) -> str:
        """Get the base URL for the OpenCode server."""
        return self._base_url

    def start(self) -> str:
        """
        Start OpenCode server if not running.

        Returns:
            The base URL for the running server

        Raises:
            RuntimeError: If server fails to start or OpenCode is not installed
        """
        # Check if already running
        if self._is_running():
            if self.logger:
                self.logger.debug(f"OpenCode server already running on {self._base_url}")
            return self._base_url

        # Check if opencode is installed
        if not self._is_opencode_installed():
            raise RuntimeError(
                "OpenCode CLI is not installed. "
                "Please install it from https://opencode.ai or via npm: npm install -g opencode"
            )

        if self.logger:
            self.logger.info(f"Starting OpenCode server on port {self.port}...")

        try:
            # Start OpenCode server process
            self.process = subprocess.Popen(
                ["opencode", "serve", "--port", str(self.port)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            # Wait for server to be ready
            self._wait_for_ready()

            # Register cleanup on exit (only once)
            if not self._cleanup_registered:
                atexit.register(self.stop)
                self._cleanup_registered = True

            if self.logger:
                self.logger.info(f"OpenCode server started successfully on {self._base_url}")

            return self._base_url

        except Exception as e:
            if self.process:
                self.process.terminate()
                self.process = None
            raise RuntimeError(f"Failed to start OpenCode server: {e}")

    def stop(self):
        """Stop the OpenCode server if running."""
        if self.process:
            if self.logger:
                self.logger.info("Stopping OpenCode server...")
            try:
                self.process.terminate()
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            self.process = None
            if self.logger:
                self.logger.info("OpenCode server stopped")

    def _is_opencode_installed(self) -> bool:
        """Check if OpenCode CLI is installed."""
        return shutil.which("opencode") is not None

    def _is_running(self) -> bool:
        """Check if server is already running on the configured port."""
        try:
            client = Opencode(base_url=self._base_url, timeout=2.0)
            client.app.get()  # Health check
            return True
        except Exception:
            return False

    def _wait_for_ready(self, timeout: int = 30):
        """
        Wait for server to be ready.

        Args:
            timeout: Maximum seconds to wait

        Raises:
            RuntimeError: If server doesn't become ready within timeout
        """
        start = time.time()
        while time.time() - start < timeout:
            if self._is_running():
                return
            time.sleep(0.5)
        raise RuntimeError(
            f"OpenCode server failed to start within {timeout} seconds. "
            "Check if the port is available and OpenCode is properly installed."
        )

    def __enter__(self):
        """Context manager entry - start server."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - stop server."""
        self.stop()
        return False
