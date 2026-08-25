import re
from pathlib import Path
from typing import List

from pydantic import BaseModel, ConfigDict, field_validator

from sampletones_shared.meta.import_boundary.lines import numbered_lines
from sampletones_shared.meta.import_boundary.violation import Violation


class TokenRule(BaseModel):
    """One tree of modules and a spelling that stays out of them.

    Attributes:
        root: Directory under the source root the pattern is written against.
        pattern: Glob naming the modules the rule reaches.
        forbidden: Regular expression the modules stay clear of.
        message: What the rule holds, printed where a module writes the spelling.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    root: str
    pattern: str
    forbidden: str
    message: str

    @field_validator("forbidden")
    @classmethod
    def _validate_the_spelling_is_a_usable_expression(
        cls,
        forbidden: str,
    ) -> str:
        """Holds the spelling to what `re` accepts, so a rule reports its own defect as it is read.

        Raises:
            ValueError: If the spelling is no valid regular expression.
        """
        try:
            re.compile(forbidden)
        except re.error as error:
            raise ValueError(f"the spelling {forbidden!r} is no valid regular expression: {error}") from error

        return forbidden

    def violations(self, path: Path) -> List[Violation]:
        """Every line of one module that writes the forbidden spelling.

        Args:
            path: Module to read.

        Returns:
            List[Violation]: The lines the rule reports, in line order.

        Raises:
            OSError: If the module cannot be read.
        """
        spelling = re.compile(self.forbidden)
        return [
            Violation.at(self.message, path, line_number, line)
            for line_number, line in numbered_lines(path)
            if spelling.search(line)
        ]
