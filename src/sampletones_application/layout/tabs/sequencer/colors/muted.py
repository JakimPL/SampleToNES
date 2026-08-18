from pydantic import BaseModel

from sampletones_application.utils.palette.colors.written import WrittenColor


class MutedColors(BaseModel, extra="forbid", frozen=True):
    """Colours marking a channel the song player silences.

    ``background`` is the neutral shade the channel takes in place of its identity tint —
    down its column in the tracker, along its row in the order table — so the channel
    recedes as a whole; ``text`` is the shade its name takes.
    """

    background: WrittenColor
    text: WrittenColor
