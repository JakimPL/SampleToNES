from __future__ import annotations

from typing import Dict

from pydantic import BaseModel, ConfigDict

from sampletones_core.formats.famitracker.model.sequence import InstrumentSequence
from sampletones_core.formats.famitracker.specification.sequences import SequenceKind


class Instrument2A03(BaseModel):
    """A FamiTracker 2A03 instrument: five sequences addressed by their kind.

    ``index`` is the instrument's slot in the module (0 for a standalone ``.fti``).
    ``sequences`` carries all five :class:`SequenceKind` entries; a kind with no
    items is written as a disabled slot.
    """

    model_config = ConfigDict(frozen=True)

    index: int
    name: str
    sequences: Dict[SequenceKind, InstrumentSequence]
