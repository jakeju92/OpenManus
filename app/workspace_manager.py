import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.config import WORKSPACE_ROOT


class WorkspaceManager:
    """Manages agent workspaces with timestamped directories for each run"""

    def __init__(self):
        self._current_workspace: Optional[Path] = None
        self._timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    @property
    def timestamp(self) -> str:
        """Get the current timestamp string"""
        return self._timestamp

    @property
    def current_workspace(self) -> Path:
        """Get the current workspace path, creating it if it doesn't exist"""
        if self._current_workspace is None:
            # Create the workspace directory with timestamp
            self._current_workspace = WORKSPACE_ROOT / self._timestamp
            os.makedirs(self._current_workspace, exist_ok=True)

        return self._current_workspace

    def get_path(self, *path_segments) -> Path:
        """Get a path inside the current workspace"""
        return self.current_workspace.joinpath(*path_segments)

    def get_git_repo_path(self, repo_name: str) -> Path:
        """Get the path for a git repository in the workspace"""
        # Extract repo name from URL if a full URL was provided
        if "/" in repo_name:
            repo_name = repo_name.split("/")[-1]
        if repo_name.endswith(".git"):
            repo_name = repo_name[:-4]

        return self.get_path(repo_name)

    def setup_logging(self, log_name: Optional[str] = None) -> Path:
        """Setup logging directory and return the log file path

        Args:
            log_name: Name prefix for the log file

        Returns:
            Path to the log file
        """
        log_dir = self.get_path("logs")
        os.makedirs(log_dir, exist_ok=True)

        # Ensure we have a valid log name
        sanitized_name = log_name
        if not sanitized_name or sanitized_name.lower() == "default":
            sanitized_name = "app"

        date_str = datetime.now().strftime("%Y-%m-%d")
        log_filename = f"{sanitized_name}_{date_str}.log"

        return log_dir / log_filename

    def cleanup(self):
        """Clean up workspace if needed"""
        # Could be used for temporary file cleanup or archiving
        pass


# Singleton instance
workspace_manager = WorkspaceManager()
