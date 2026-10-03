from dataclasses import dataclass
from typing import Final, Optional, Tuple

from tests.screens.application.old_files.constants import VANISHED
from tests.screens.application.old_files.steps import damaged_name
from tests.suite.screens.seeds.archives import Damage


@dataclass(frozen=True)
class StartupCase:
    """One row of a startup table: a broken document handed over at start.

    Attributes: damage: The damage done to the file, or None for a file that is gone.
    """

    damage: Optional[Damage]

    def name(self, suffix: str) -> str:
        """The file name of the row's document with ``suffix``: the damage's name, or the vanished file's."""
        return damaged_name(self.damage, suffix) if self.damage is not None else f"{VANISHED}{suffix}"


STARTUP_CASES: Final[Tuple[StartupCase, ...]] = (*(StartupCase(damage) for damage in Damage), StartupCase(None))
