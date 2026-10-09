from pathlib import Path
from typing import NamedTuple, Self


class Violation(NamedTuple):
    """One import or token a rule forbids, and where a reader opens it.

    Attributes:
        kind: What the rule forbids, spelled the way the report names it.
        location: The module, the line number and the line itself.
    """

    kind: str
    location: str

    @classmethod
    def at(cls, kind: str, path: Path, line_number: int, line: str) -> Self:
        """One violation located as `path:line`, the form an editor jumps to.

        Args:
            kind: What the rule forbids.
            path: Module the line sits in.
            line_number: Line the violation sits on, counting from one.
            line: The line itself, quoted stripped of its indentation.

        Returns:
            Self: The violation a report prints.
        """
        return cls(
            kind=kind,
            location=f"{path}:{line_number}: {line.strip()}",
        )
