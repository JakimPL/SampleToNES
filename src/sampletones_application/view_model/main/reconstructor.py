from typing import FrozenSet, Optional, Tuple

from pydantic import BaseModel

from sampletones_application.constants.sources import SettingsField
from sampletones_application.view_model.shared.agreement import Agreement
from sampletones_core.constants.enums import ChannelName


class SettingsSlotViewModel(BaseModel, frozen=True):
    """One per-recording choice as the settings card draws it: a box per channel it offers.

    ``held_channels`` are the ones every recording the card inspects makes the choice on and
    ``partial_channels`` the ones only some of them do, so a folder reads the same three ways in
    the card as it does in the list.
    """

    field: SettingsField
    offered_channels: FrozenSet[ChannelName]
    held_channels: FrozenSet[ChannelName]
    partial_channels: FrozenSet[ChannelName]

    def offers(self, channel_name: ChannelName) -> bool:
        """Whether this choice is put to a reader on ``channel_name``."""
        return channel_name in self.offered_channels

    def agreement_on(self, channel_name: ChannelName) -> Agreement:
        """How the recordings the card inspects read on ``channel_name``."""
        if channel_name in self.held_channels:
            return Agreement.ALL

        return Agreement.SOME if channel_name in self.partial_channels else Agreement.NONE


class ReconstructorPanelViewModel(BaseModel, frozen=True):
    """What the settings card shows: the choices it edits, and what it is editing them on.

    ``inspected`` names the row a reader picked out of the list; with none picked the card edits
    the settings a recording joins the list with, which is what every new row starts from.
    """

    slots: Tuple[SettingsSlotViewModel, ...]
    inspected: Optional[str]
    drive: float

    @property
    def channels(self) -> FrozenSet[ChannelName]:
        """The channels the run hands out, which is the first slot's own reading."""
        for slot in self.slots:
            if slot.field is SettingsField.CHANNELS:
                return slot.held_channels

        return frozenset()
