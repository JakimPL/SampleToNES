from typing import Dict, Final

from sampletones_application.tags.general import (
    TAG_GLOBAL_THEME_CHANNEL_NOISE,
    TAG_GLOBAL_THEME_CHANNEL_PULSE1,
    TAG_GLOBAL_THEME_CHANNEL_PULSE2,
    TAG_GLOBAL_THEME_CHANNEL_TRIANGLE,
)
from sampletones_core.constants.enums import GeneratorName

CHANNEL_THEME_TAGS: Final[Dict[GeneratorName, str]] = {
    GeneratorName.PULSE1: TAG_GLOBAL_THEME_CHANNEL_PULSE1,
    GeneratorName.PULSE2: TAG_GLOBAL_THEME_CHANNEL_PULSE2,
    GeneratorName.TRIANGLE: TAG_GLOBAL_THEME_CHANNEL_TRIANGLE,
    GeneratorName.NOISE: TAG_GLOBAL_THEME_CHANNEL_NOISE,
}
