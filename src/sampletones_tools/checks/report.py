import sys
from typing import Sequence


def report_findings(lines: Sequence[str], *, heading: str, total: str) -> int:
    """Prints a check's findings on the standard error stream and answers with the exit status.

    Every check reports the same way, so a reader meets one shape however the check differs: the
    heading, one indented line per finding and the count, filled into ``total`` as ``{count}``.

    Returns:
        int: ``0`` where nothing was found, ``1`` otherwise.
    """
    if not lines:
        return 0

    print(heading, file=sys.stderr)
    for line in lines:
        print(f"  {line}", file=sys.stderr)

    print(f"\n{total.format(count=len(lines))}", file=sys.stderr)
    return 1
