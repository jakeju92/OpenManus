import asyncio
import os
import shlex
from typing import List, Optional

from pydantic import Field

from app.config import config
from app.logger import logger
from app.tool.base import BaseTool, CLIResult
from app.workspace_manager import workspace_manager


class GitTool(BaseTool):
    name: str = "git_operations"
    description: str = """Perform Git operations on repositories.
Use this tool when you need to clone a repository, commit changes, push to remote, or manage git stashes.
This tool allows for standard git operations including clone, pull, commit, push, stash, and branch management.
When cloning repositories, you need to provide a valid git URL and optionally a target directory.
For other operations like commit, push, and stash, the current working directory must be a git repository.
By default, repositories are cloned into the current workspace directory.
"""
    parameters: dict = {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "description": "(required) The git operation to perform. Available operations: clone, status, add, commit, push, pull, stash, stash_pop, branch, checkout, log",
                "enum": ["clone", "status", "add", "commit", "push", "pull", "stash", "stash_pop", "stash_list", "branch", "checkout", "log"],
            },
            "repo_url": {
                "type": "string",
                "description": "The URL of the git repository (required for clone operation)",
            },
            "target_dir": {
                "type": "string",
                "description": "Target directory for clone operation (optional, defaults to workspace directory)",
            },
            "commit_message": {
                "type": "string",
                "description": "Commit message (required for commit operation)",
            },
            "files": {
                "type": "array",
                "items": {
                    "type": "string"
                },
                "description": "List of files to add (for add operation, defaults to all changes with '.')",
            },
            "branch_name": {
                "type": "string",
                "description": "Branch name (required for checkout or branch operations)",
            },
            "stash_message": {
                "type": "string",
                "description": "Optional message for stash operation",
            },
        },
        "required": ["operation"],
    }

    process: Optional[asyncio.subprocess.Process] = None
    current_path: str = os.getcwd()
    lock: asyncio.Lock = asyncio.Lock()
    workspace_root: str = Field(default="", description="Path to the workspace root")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Set default workspace path from workspace manager
        self.workspace_root = str(workspace_manager.current_workspace)

    async def execute(
        self,
        operation: str,
        repo_url: Optional[str] = None,
        target_dir: Optional[str] = None,
        commit_message: Optional[str] = None,
        files: Optional[List[str]] = None,
        branch_name: Optional[str] = None,
        stash_message: Optional[str] = None
    ) -> CLIResult:
        """
        Execute a git operation.

        Args:
            operation: The git operation to perform
            repo_url: URL of the repository (for clone)
            target_dir: Target directory (for clone)
            commit_message: Commit message (for commit)
            files: List of files (for add)
            branch_name: Branch name (for branch operations)
            stash_message: Message for stash operation

        Returns:
            CLIResult: The result of the git operation
        """
        # If cloning, prepare target directory in workspace
        if operation == "clone":
            # Set working directory to workspace root for clone operations
            await self.set_working_directory(self.workspace_root)

            # If no target directory is specified, extract one from the repo URL
            if not target_dir and repo_url:
                # Extract repo name from URL
                if "/" in repo_url:
                    repo_name = repo_url.split("/")[-1]
                    if repo_name.endswith(".git"):
                        repo_name = repo_name[:-4]
                else:
                    repo_name = repo_url

                # Use repo name as target directory
                target_dir = repo_name

            logger.info(f"Cloning repository to workspace: {self.workspace_root}/{target_dir}")

        cmd = await self._build_git_command(
            operation=operation,
            repo_url=repo_url,
            target_dir=target_dir,
            commit_message=commit_message,
            files=files,
            branch_name=branch_name,
            stash_message=stash_message
        )

        if not cmd:
            return CLIResult(error="Invalid git operation or missing required parameters")

        async with self.lock:
            try:
                logger.info(f"Executing git command: {cmd} in {self.current_path}")
                self.process = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=self.current_path,
                )
                stdout, stderr = await self.process.communicate()

                # Update current path if cloning into a specified directory
                if operation == "clone" and target_dir:
                    clone_dir = os.path.join(self.current_path, target_dir)
                    if os.path.isdir(clone_dir):
                        self.current_path = clone_dir
                        logger.info(f"Changed working directory to: {self.current_path}")

                result = CLIResult(
                    output=stdout.decode().strip(),
                    error=stderr.decode().strip(),
                )
                return result
            except Exception as e:
                logger.error(f"Git operation failed: {str(e)}")
                return CLIResult(error=str(e))
            finally:
                self.process = None

    async def _build_git_command(
        self,
        operation: str,
        repo_url: Optional[str] = None,
        target_dir: Optional[str] = None,
        commit_message: Optional[str] = None,
        files: Optional[List[str]] = None,
        branch_name: Optional[str] = None,
        stash_message: Optional[str] = None
    ) -> Optional[str]:
        """
        Build the git command based on the operation and parameters.

        Args:
            operation: The git operation
            repo_url: Repository URL
            target_dir: Target directory
            commit_message: Commit message
            files: List of files
            branch_name: Branch name
            stash_message: Stash message

        Returns:
            str: The constructed git command
        """
        if operation == "clone":
            if not repo_url:
                return None

            cmd = f"git clone {shlex.quote(repo_url)}"
            if target_dir:
                cmd += f" {shlex.quote(target_dir)}"
            return cmd

        elif operation == "status":
            return "git status"

        elif operation == "add":
            if not files:
                return "git add ."
            else:
                files_quoted = " ".join(shlex.quote(f) for f in files)
                return f"git add {files_quoted}"

        elif operation == "commit":
            if not commit_message:
                return None
            return f"git commit -m {shlex.quote(commit_message)}"

        elif operation == "push":
            return "git push"

        elif operation == "pull":
            return "git pull"

        elif operation == "stash":
            cmd = "git stash"
            if stash_message:
                cmd += f" push -m {shlex.quote(stash_message)}"
            return cmd

        elif operation == "stash_pop":
            return "git stash pop"

        elif operation == "stash_list":
            return "git stash list"

        elif operation == "branch":
            if not branch_name:
                return "git branch"
            return f"git branch {shlex.quote(branch_name)}"

        elif operation == "checkout":
            if not branch_name:
                return None
            return f"git checkout {shlex.quote(branch_name)}"

        elif operation == "log":
            return "git log --oneline --graph --decorate -n 10"

        return None

    async def set_working_directory(self, path: str) -> CLIResult:
        """
        Set the working directory for git operations.

        Args:
            path: The path to set as working directory

        Returns:
            CLIResult: Result indicating success or failure
        """
        try:
            if not os.path.isabs(path):
                path = os.path.join(self.current_path, path)

            path = os.path.abspath(path)

            if os.path.isdir(path):
                self.current_path = path
                return CLIResult(
                    output=f"Changed git working directory to {self.current_path}",
                    error=""
                )
            else:
                return CLIResult(
                    output="",
                    error=f"No such directory: {path}"
                )
        except Exception as e:
            return CLIResult(output="", error=str(e))

    async def close(self):
        """Close the git process if it exists."""
        async with self.lock:
            if self.process:
                self.process.terminate()
                try:
                    await asyncio.wait_for(self.process.wait(), timeout=5)
                except asyncio.TimeoutError:
                    self.process.kill()
                    await self.process.wait()
                finally:
                    self.process = None

    async def __aenter__(self):
        """Enter the asynchronous context manager."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the asynchronous context manager and close the process."""
        await self.close()
