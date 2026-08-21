from typing import Optional, Tuple

from pydantic import BaseModel

from sampletones_core.constants.enums import ChannelName, HierarchyMode


class StemViewModel(BaseModel, frozen=True):
    """One stem row: its identity, source file, channels, and selection."""

    stem_id: int
    label: str
    channels: Tuple[ChannelName, ...]
    enabled: bool
    selected: bool


class ReconstructionStemsViewModel(BaseModel, frozen=True):
    """What the stems card renders for the loaded reconstruction."""

    reconstruction_loaded: bool
    stems: Tuple[StemViewModel, ...]
    hierarchy_mode: Optional[HierarchyMode] = None
    channel_cap: Optional[int] = None

    @property
    def show_setup_line(self) -> bool:
        """The setup line states the hierarchy mode and cap a stems record carries."""
        return self.hierarchy_mode is not None

    @property
    def show_empty_state(self) -> bool:
        """The empty state explains a loaded reconstruction that records no source."""
        return self.reconstruction_loaded and not self.stems
