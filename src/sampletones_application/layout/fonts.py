from enum import Enum

from pydantic import BaseModel


class Typeface(Enum):
    SANS = "sans"
    MONO = "mono"
    ICON = "icon"


class Step(Enum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class FontScale(BaseModel, extra="forbid", frozen=True):
    small: int
    medium: int
    large: int

    def step(self, step: Step) -> int:
        return {
            Step.SMALL: self.small,
            Step.MEDIUM: self.medium,
            Step.LARGE: self.large,
        }[step]


class FontsLayout(BaseModel, extra="forbid", frozen=True):
    """Per-typeface pixel-size scales for every rendered font.

    Each typeface carries its own ``small``/``medium``/``large`` scale, so Sans and
    Mono are tuned to the same apparent size independently. ``scale`` is the DearPyGui
    global font multiplier applied on top.
    """

    scale: int
    sans: FontScale
    mono: FontScale
    icon: FontScale

    def size_for(self, typeface: Typeface, step: Step) -> int:
        scale = {
            Typeface.SANS: self.sans,
            Typeface.MONO: self.mono,
            Typeface.ICON: self.icon,
        }[typeface]
        return scale.step(step)
