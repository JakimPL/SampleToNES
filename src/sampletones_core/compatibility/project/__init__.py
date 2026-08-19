from typing import Final, Tuple

from sampletones_core.compatibility.update import VersionUpdate

from .v1_1 import V1_1

UPDATES: Final[Tuple[VersionUpdate, ...]] = (V1_1,)
