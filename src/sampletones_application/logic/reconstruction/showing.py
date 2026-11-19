from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, Protocol

from sampletones_application.view_model.shared.waveform_data import WaveformData


class Drawing(Enum):
    """How a showing draws the waveform: loaded afresh after a listening change, or updated in place after an edit."""

    LOAD = "load"
    UPDATE = "update"


@dataclass(frozen=True)
class OwedShowing:
    """What the screen owes the reader of the document's sound, settled once the worker has rendered what
    the reader hears.

    Every gesture that reads the sound joins what is owed, so a flip of the source during an
    opening still loads the waveform, and a retune followed by a flip still re-fits it.

    Attributes:
        drawing: How the waveform is drawn, or ``None`` where the showing plays or writes alone.
        refit: Whether the waveform's view is re-fitted to the audio's length.
        play: Whether the audio is handed to the player.
        export_to: The file what plays is written to, where an export waits for the sound.
    """

    drawing: Optional[Drawing]
    refit: bool
    play: bool
    export_to: Optional[Path]

    def joined(self, later: OwedShowing) -> OwedShowing:
        """What is owed once ``later`` is asked for on top of this: every showing kept, the newest export's file."""
        return OwedShowing(
            drawing=self._drawn_either(self.drawing, later.drawing),
            refit=self.refit or later.refit,
            play=self.play or later.play,
            export_to=later.export_to if later.export_to is not None else self.export_to,
        )

    @staticmethod
    def _drawn_either(
        first: Optional[Drawing],
        second: Optional[Drawing],
    ) -> Optional[Drawing]:
        """The drawing covering both: a load draws everything an update would, so it outranks one."""
        drawings = {first, second}
        if Drawing.LOAD in drawings:
            return Drawing.LOAD

        if Drawing.UPDATE in drawings:
            return Drawing.UPDATE

        return None


class WaveformUpdate(Protocol):
    """What draws an updated waveform in place, re-fitting its view to the audio's length where asked.

    The waveform is handed over by position, so a drawer may name it as it likes.
    """

    def __call__(
        self,
        waveform: WaveformData,
        /,
        *,
        refit: bool,
    ) -> None: ...
