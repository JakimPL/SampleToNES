from typing import Final, Optional, Tuple

from sampletones_core.constants.enums import GeneratorName

CHANNEL_AXIS: Final[Tuple[Optional[GeneratorName], ...]] = (None,) + tuple(GeneratorName.items())
