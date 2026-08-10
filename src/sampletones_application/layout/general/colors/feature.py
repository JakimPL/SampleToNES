from pydantic import BaseModel

from sampletones_application.utils.palette.colors.written import WrittenColor


class FeatureColors(BaseModel, extra="forbid", frozen=True):
    """The per-feature palette shared by every view that names a feature.

    The details tab's bar plots and the history panel's detail segments both
    paint from this block, so a feature keeps one colour across the
    application.
    """

    volume: WrittenColor
    arpeggio: WrittenColor
    pitch: WrittenColor
    duty_cycle: WrittenColor
