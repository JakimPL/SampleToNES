from enum import StrEnum
from typing import Final, FrozenSet, Tuple

from pydantic import BaseModel

from sampletones_core.constants.enums import GeneratorName


class ReconstructionPathState(StrEnum):
    """Whether a path can be shown for a reconstruction location.

    ``AVAILABLE`` carries a resolvable path. ``NOT_FOUND`` marks a recorded path whose
    file is absent on this machine. ``NOT_APPLICABLE`` marks a location that a
    reconstruction does not have (a sequencer sample keeps no file locations).
    ``EMPTY`` is the resting state when no reconstruction is loaded.
    """

    AVAILABLE = "available"
    NOT_FOUND = "not_found"
    NOT_APPLICABLE = "not_applicable"
    EMPTY = "empty"


RECORDED_PATH_STATES: Final[Tuple[ReconstructionPathState, ...]] = (
    ReconstructionPathState.AVAILABLE,
    ReconstructionPathState.NOT_FOUND,
)


class ReconstructionPathViewModel(BaseModel, frozen=True):
    state: ReconstructionPathState
    path: str


class ReconstructionViewModel(BaseModel, frozen=True):
    """What the reconstruction view renders, including which channels the waveform offers.

    A channel plays once its instruction stream describes a frame, which is what makes its
    generator checkbox reachable; :attr:`selected_generators` is the subset the reader keeps
    switched on, so a channel switched off by hand stays off across an edit.
    """

    reconstruction_loaded: bool
    playing_generators: FrozenSet[GeneratorName]
    selected_generators: FrozenSet[GeneratorName]
    reconstruction_file: ReconstructionPathViewModel
    original_audio: ReconstructionPathViewModel

    @property
    def audio_source_enabled(self) -> bool:
        """The source toggle offers the original audio once its file is present on disk;
        until then playback stays on the reconstruction."""
        return self.original_audio.state is ReconstructionPathState.AVAILABLE

    @property
    def locate_audio_enabled(self) -> bool:
        """Locating needs a recorded path to point the file explorer at; the file
        itself may have moved since the reconstruction was generated."""
        return self.original_audio.state in RECORDED_PATH_STATES

    @property
    def show_locate_audio_hint(self) -> bool:
        """The hint explains the disabled locate button, so it appears exactly when a
        loaded reconstruction keeps no original audio path."""
        return self.reconstruction_loaded and self.original_audio.state is ReconstructionPathState.NOT_APPLICABLE
