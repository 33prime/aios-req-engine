"""Git repository management for prototype repos.

Uses subprocess.run for simplicity — no GitPython dependency.
"""

import os
import subprocess
from pathlib import Path

from app.core.logging import get_logger

logger = get_logger(__name__)


class GitError(Exception):
    """Raised when a git operation fails."""


class GitManager:
    """Manages git operations for prototype repositories."""

    def __init__(self, base_dir: str = "/tmp/aios-prototypes"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _run(
        self, args: list[str], cwd: str | None = None, check: bool = True
    ) -> subprocess.CompletedProcess[str]:
        """Run a git command and return the result."""
        cmd = ["git"] + args
        logger.debug(f"Running: {' '.join(cmd)} in {cwd or 'default'}")
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=120,
                check=check,
            )
            return result
        except subprocess.CalledProcessError as e:
            logger.error(f"Git command failed: {' '.join(cmd)}\nstderr: {e.stderr}")
            raise GitError(f"git {args[0]} failed: {e.stderr.strip()}") from e
        except subprocess.TimeoutExpired as e:
            raise GitError(f"git {args[0]} timed out after 120s") from e

    def clone(self, repo_url: str, project_id: str) -> str:
        """Clone a repo to {base_dir}/{project_id}. Returns local path."""
        local_path = str(self.base_dir / project_id)
        if Path(local_path).exists():
            logger.info(f"Repo already exists at {local_path}, pulling latest")
            self._run(["pull", "--ff-only"], cwd=local_path, check=False)
            return local_path
        self._run(["clone", repo_url, local_path])
        logger.info(f"Cloned {repo_url} to {local_path}")
        return local_path

    def create_branch(self, local_path: str, branch_name: str) -> None:
        """Create and checkout a new branch."""
        self._run(["checkout", "-b", branch_name], cwd=local_path)
        logger.info(f"Created branch {branch_name}")

    def checkout(self, local_path: str, branch_name: str) -> None:
        """Checkout an existing branch."""
        self._run(["checkout", branch_name], cwd=local_path)

    def commit(
        self, local_path: str, message: str, files: list[str] | None = None
    ) -> str:
        """Stage files and commit. Returns commit SHA."""
        if files:
            for f in files:
                self._run(["add", f], cwd=local_path)
        else:
            self._run(["add", "-A"], cwd=local_path)
        self._run(["commit", "-m", message], cwd=local_path)
        result = self._run(["rev-parse", "HEAD"], cwd=local_path)
        sha = result.stdout.strip()
        logger.info(f"Committed {sha[:8]}: {message}")
        return sha

    def push(self, local_path: str, branch: str | None = None) -> None:
        """Push current branch to origin."""
        args = ["push"]
        if branch:
            args.extend(["origin", branch])
        self._run(args, cwd=local_path)

    def get_file_tree(
        self, local_path: str, extensions: list[str] | None = None
    ) -> list[str]:
        """List all files in repo, optionally filtered by extension."""
        all_files = []
        for root, _dirs, files in os.walk(local_path):
            # Skip .git directory
            if ".git" in root.split(os.sep):
                continue
            for f in files:
                rel_path = os.path.relpath(os.path.join(root, f), local_path)
                if extensions:
                    if any(rel_path.endswith(ext) for ext in extensions):
                        all_files.append(rel_path)
                else:
                    all_files.append(rel_path)
        return sorted(all_files)

    def read_file(self, local_path: str, file_path: str) -> str:
        """Read a file from the repo."""
        full_path = Path(local_path) / file_path
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        return full_path.read_text(encoding="utf-8")

    def write_file(self, local_path: str, file_path: str, content: str) -> None:
        """Write content to a file in the repo."""
        full_path = Path(local_path) / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")
        logger.debug(f"Wrote {len(content)} chars to {file_path}")
