from enum import Enum

from pydantic import BaseModel


class Typeface(Enum):
    SANS = "sans"
    MONO = "mono"
    ICON = "icon"


class Step(Enum):
    TINY = "tiny"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    TITLE = "title"


class FontScale(BaseModel, extra="forbid", frozen=True):
    tiny: int
    small: int
    medium: int
    large: int
    title: int

    def step(self, step: Step) -> int:
        return {
            Step.TINY: self.tiny,
            Step.SMALL: self.small,
            Step.MEDIUM: self.medium,
            Step.LARGE: self.large,
            Step.TITLE: self.title,
        }[step]


class FontsLayout(BaseModel, extra="forbid", frozen=True):
    """Per-typeface pixel-size scales for every rendered font.

    Each typeface carries its own ``tiny``/``small``/``medium``/``large``/``title`` scale, so Sans
    and Mono are tuned to the same apparent size independently, and a rung is drawn at
    where a font asks for it. ``scale`` is the DearPyGui global font multiplier applied
    on top.
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
