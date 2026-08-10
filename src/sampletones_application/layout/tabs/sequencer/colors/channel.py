from pydantic import BaseModel

from sampletones_application.utils.palette.colors.written import WrittenColor


class ChannelColors(BaseModel, extra="forbid", frozen=True):
    """Per-channel identity colours shared by the order table and the tracker grid.

    The order table paints each channel's row label in its colour; the tracker grid
    tints each channel's column background with the same colour at a low alpha, so a
    channel keeps one identity across both views.
    """

    pulse1: WrittenColor
    pulse2: WrittenColor
    triangle: WrittenColor
    noise: WrittenColor
