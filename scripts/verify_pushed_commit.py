import argparse
import os
import sys
from pathlib import Path
from typing import Final, Optional, Sequence

from bootstrap.checked_commits import is_checked, short_commit
from bootstrap.layout import repository_root

PUSHED_COMMIT_VARIABLE: Final[str] = "PRE_COMMIT_TO_REF"
UNCHECKED: Final[str] = (
    "The push sends commit {commit}, whose files haven't passed `make check`. "
    "Run `make check` on that commit, then push again."
)


def push_failure(root: Path, pushed: Optional[str]) -> Optional[str]:
    """What holds a push back: the commit it sends, until ``make check`` has passed on its files.

    pre-commit names the commit a push sends in ``PRE_COMMIT_TO_REF``. A push it names no commit
    for, such as a branch deletion, goes through.

    Args:
        root: The repository the push leaves from.
        pushed: The commit or tag the push sends.

    Returns:
        Optional[str]: The refusal as one line, or ``None`` for a push that goes through.
    """
    if pushed is None or is_checked(root, pushed):
        return None

    return UNCHECKED.format(commit=short_commit(root, pushed))


def main(argv: Sequence[str]) -> int:
    """Lets a push through once ``make check`` has passed on the commit it sends; the pre-push hook runs it."""
    parser = argparse.ArgumentParser(description="Let a push through once `make check` has passed on its commit.")
    parser.parse_args(list(argv))

    failure = push_failure(repository_root(), os.environ.get(PUSHED_COMMIT_VARIABLE))
    if failure is not None:
        print(failure)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
