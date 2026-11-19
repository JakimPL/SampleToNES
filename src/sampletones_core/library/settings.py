from __future__ import annotations

from dataclasses import dataclass

from sampletones_core.configs import Config, InstructionsLibraryConfig, PitchRange


@dataclass(frozen=True)
class LibrarySettings:
    """The settings a library is built under: the library section and the notes it holds.

    Together they decide what a library holds, so its name hashes both and its file states both.
    """

    library: InstructionsLibraryConfig
    pitch_range: PitchRange

    @classmethod
    def of(cls, config: Config) -> LibrarySettings:
        return cls(library=config.library, pitch_range=config.general.pitch_range)
