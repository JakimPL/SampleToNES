from typing import Optional

from sampletones_core.project.voices.instrument import Instrument


class HeldInstrument:
    """The Reconstructions tab holding one instrument, which is all an audition reads of the tab."""

    def __init__(self, instrument: Instrument) -> None:
        self._instrument = instrument

    @property
    def instrument(self) -> Optional[Instrument]:
        return self._instrument
