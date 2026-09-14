from typing import Final, Tuple

from sampletones_core.compatibility.update import VersionUpdate

from .v2_1 import V2_1

UPDATES: Final[Tuple[VersionUpdate, ...]] = (V2_1,)
