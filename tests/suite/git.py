import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Final, Tuple

GIT_IDENTITY: Final[Dict[str, str]] = {
    "GIT_AUTHOR_NAME": "Tester",
    "GIT_AUTHOR_EMAIL": "tester@example.com",
    "GIT_COMMITTER_NAME": "Tester",
    "GIT_COMMITTER_EMAIL": "tester@example.com",
}
UNSIGNED: Final[Tuple[str, ...]] = ("-c", "commit.gpgsign=false", "-c", "tag.gpgsign=false")
FIRST_FILE: Final[str] = "module.py"


@dataclass(frozen=True)
class ScratchRepository:
    """A git repository a test builds its history in, committing under an identity of its own, unsigned.

    Attributes:
        root: The repository's work tree.
    """

    root: Path

    def git(self, *arguments: str) -> str:
        """Runs git in the work tree and answers with what it printed, stripped."""
        completed = subprocess.run(
            ["git", *UNSIGNED, *arguments],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
            env={**os.environ, **GIT_IDENTITY},
        )
        return completed.stdout.strip()

    def write(self, name: str, text: str) -> None:
        """Writes ``text`` to the file ``name`` in the work tree."""
        (self.root / name).write_text(text, encoding="utf-8")

    def commit(self, message: str) -> str:
        """Commits every file of the work tree and answers with the new commit's hash."""
        self.git("add", "--all")
        self.git("commit", "--quiet", "--allow-empty", "--message", message)
        return self.git("rev-parse", "HEAD")
