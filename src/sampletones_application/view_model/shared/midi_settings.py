from typing import Optional, Tuple

from pydantic import BaseModel

from sampletones_core.utils.frequencies import pitch_to_name
from sampletones_shared.constants.music import LIMIT_MAX_PITCH, LIMIT_MIN_PITCH


class MidiSettingsViewModel(BaseModel, frozen=True):
    """What the MIDI settings dialog shows: the inputs, the one read, and how its keys are read.

    Attributes:
        available: Whether a MIDI library loaded on this computer.
        ports: The names of the inputs as the latest listing found them.
        port: The input read now, or ``None`` while none is.
        velocity_sets_volume: Whether how hard a key is struck sets its volume.
        refusal: Why the input last picked could not be opened, or ``None`` where it opened.
    """

    available: bool
    ports: Tuple[str, ...]
    port: Optional[str]
    velocity_sets_volume: bool
    refusal: Optional[str]

    def port_items(self, no_input: str) -> Tuple[str, ...]:
        """The choices the input combo offers: no input first, then every input listed."""
        return (no_input, *self.ports)

    def port_item(self, no_input: str) -> str:
        """The choice standing for the input read now."""
        return no_input if self.port is None else self.port


def key_name(note: int, *, number_template: str) -> str:
    """The name the dialog gives a key: its note name where the application names that note.

    Args:
        note: The MIDI note number of the key.
        number_template: How a key below or above the named notes is named, by its ``number``.
    """
    return pitch_to_name(note) if LIMIT_MIN_PITCH <= note <= LIMIT_MAX_PITCH else number_template.format(number=note)
