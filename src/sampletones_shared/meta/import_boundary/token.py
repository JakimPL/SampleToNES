import re
from pathlib import Path
from typing import List, NamedTuple

from sampletones_shared.meta.import_boundary.lines import numbered_lines
from sampletones_shared.meta.import_boundary.violation import Violation


class TokenRule(NamedTuple):
    """One tree of modules and a spelling that stays out of them.

    Attributes:
        root: Directory under the source root the pattern is written against.
        pattern: Glob naming the modules the rule reaches.
        forbidden: Regular expression the modules stay clear of.
        message: What the rule holds, printed where a module writes the spelling.
    """

    root: str
    pattern: str
    forbidden: str
    message: str

    def violations(self, path: Path) -> List[Violation]:
        """Every line of one module that writes the forbidden spelling.

        Args:
            path: Module to read.

        Returns:
            List[Violation]: The lines the rule reports, in line order.

        Raises:
            OSError: If the module cannot be read.
            re.error: If the forbidden spelling is no valid regular expression.
        """
        spelling = re.compile(self.forbidden)
        return [
            Violation.at(self.message, path, line_number, line)
            for line_number, line in numbered_lines(path)
            if spelling.search(line)
        ]
