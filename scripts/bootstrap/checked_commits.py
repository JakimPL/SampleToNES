import subprocess
from pathlib import Path
from typing import Final, List, Optional

from bootstrap.layout import CHECKED_TREES_RECORD

GIT: Final[str] = "git"
KEPT_TREES: Final[int] = 500


def clean_tree(root: Path) -> Optional[str]:
    """The files of the commit checked out at ``root``, while the work tree holds exactly them.

    Args:
        root: A directory of the repository.

    Returns:
        Optional[str]: The hash of the commit's tree, or ``None`` while a file is changed, staged or
            untracked.
    """
    if _git(root, "status", "--porcelain", "--untracked-files=normal"):
        return None

    return commit_tree(root, "HEAD")


def commit_tree(root: Path, revision: str) -> str:
    """The hash of the tree ``revision`` holds; a tag holds the tree of the commit it names.

    Args:
        root: A directory of the repository.
        revision: A commit, a tag or any other name git reads as one.
    """
    return _git(root, "rev-parse", "--verify", f"{revision}^{{tree}}")


def short_commit(root: Path, revision: str) -> str:
    """The abbreviated hash git prints for ``revision``, which names a commit to a developer.

    Args:
        root: A directory of the repository.
        revision: A commit, a tag or any other name git reads as one.
    """
    return _git(root, "rev-parse", "--short", revision)


def is_checked(root: Path, revision: str) -> bool:
    """Whether ``make check`` passed on the files ``revision`` holds, in any worktree of the repository.

    Args:
        root: A directory of the repository.
        revision: A commit, a tag or any other name git reads as one.
    """
    return commit_tree(root, revision) in checked_trees(root)


def checked_trees(root: Path) -> List[str]:
    """The trees marked as checked, oldest first.

    A mark names the files a check passed on, so every commit holding those files carries it. The
    record lives in the git directory every worktree of the repository shares, so a check run in
    one worktree serves a push from any other.

    Args:
        root: A directory of the repository.
    """
    record = _record_path(root)
    return record.read_text(encoding="utf-8").split() if record.is_file() else []


def mark_checked(root: Path, tree: str) -> None:
    """Marks ``tree`` as checked, as the newest mark, keeping the newest ``KEPT_TREES`` marks.

    Args:
        root: A directory of the repository.
        tree: The hash of the tree every check passed on.
    """
    marked = [current for current in checked_trees(root) if current != tree]
    marked.append(tree)
    _record_path(root).write_text("\n".join(marked[-KEPT_TREES:]) + "\n", encoding="utf-8")


def _record_path(root: Path) -> Path:
    common = _git(root, "rev-parse", "--path-format=absolute", "--git-common-dir")
    return Path(common) / CHECKED_TREES_RECORD


def _git(root: Path, *arguments: str) -> str:
    completed = subprocess.run([GIT, *arguments], cwd=root, check=True, capture_output=True, text=True)
    return completed.stdout.strip()
