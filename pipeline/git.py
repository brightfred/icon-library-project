# pipeline/git.py
import subprocess
from pathlib import Path

from pipeline.config import ROOT, GIT_COMMIT_PREFIX, GIT_COMMIT_SUFFIX


class GitPublisher:
    """
    Handles staging, committing, and pushing changes to GitHub.
    Single responsibility: git operations only.
    All other classes are unaware that git exists.
    """

    def __init__(self, repo_root: Path = ROOT):
        self._root = repo_root

    def publish(self, icon_name: str) -> bool:
        """
        Stage all changes, commit, and push.
        Returns True on success, False on any failure.
        """
        return (
            self._stage()
            and self._commit(icon_name)
            and self._push()
        )

    def stage(self) -> bool:
        return self._stage()

    def commit(self, icon_name: str) -> bool:
        return self._commit(icon_name)

    def push(self) -> bool:
        return self._push()

    def has_changes(self) -> bool:
        """Return True if there are staged or unstaged changes."""
        result = self._run(["git", "status", "--porcelain"])
        return bool(result.stdout.strip())

    # ── Private helpers ───────────────────────────────────────────────────────

    def _stage(self) -> bool:
        result = self._run(["git", "add", "-A"])
        return result.returncode == 0

    def _commit(self, icon_name: str) -> bool:
        message = f"{GIT_COMMIT_PREFIX} {icon_name} {GIT_COMMIT_SUFFIX}"
        result  = self._run(["git", "commit", "-m", message])
        return result.returncode == 0

    def _push(self) -> bool:
        result = self._run(["git", "push"])
        return result.returncode == 0

    def _run(self, cmd: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(
            cmd,
            cwd=str(self._root),
            capture_output=True,
            text=True,
        )