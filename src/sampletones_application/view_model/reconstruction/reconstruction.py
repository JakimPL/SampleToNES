from typing import FrozenSet

from pydantic import BaseModel

from sampletones_core.constants.enums import ChannelName

from .paths.path import ReconstructionPathViewModel
from .paths.state import (
    PLAYABLE_PATH_STATES,
    RECORDED_PATH_STATES,
    ReconstructionPathState,
)


class ReconstructionViewModel(BaseModel, frozen=True):
    """What the reconstruction view renders, including which channels the waveform offers.

    A channel plays once its instruction stream describes a frame, which is what makes its
    channel checkbox reachable; :attr:`selected_channels` is the subset the reader keeps
    switched on, so a channel switched off by hand stays off across an edit.
    """

    reconstruction_loaded: bool
    playing_channels: FrozenSet[ChannelName]
    selected_channels: FrozenSet[ChannelName]
    reconstruction_file: ReconstructionPathViewModel
    original_audio: ReconstructionPathViewModel

    @property
    def audio_source_enabled(self) -> bool:
        """The source toggle offers the original audio once its file is present on disk;
        until then playback stays on the reconstruction."""
        return self.original_audio.state in PLAYABLE_PATH_STATES

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
