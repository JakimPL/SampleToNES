from typing import FrozenSet, Optional, Tuple

from pydantic import BaseModel

from sampletones_application.constants.sources import SettingsField, SourceKind
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


class InspectedSourceViewModel(BaseModel, frozen=True):
    """The row the settings card is editing, as the card names it.

    A folder reads its own name and how many recordings it stands for, so the card says what a
    choice made here reaches; a recording reads its name alone.
    """

    name: str
    kind: SourceKind
    holds: int

    @property
    def stands_for_a_folder(self) -> bool:
        """The row is a folder, so its count is part of what names it."""
        return self.kind is SourceKind.FOLDER


class SourceSettingsPanelViewModel(BaseModel, frozen=True):
    """What the settings card shows: the choices it edits, and the row it edits them on.

    ``inspected`` names the row a reader picked out of the converter's list, which is the whole of
    what the choices below it reach. ``drive`` holds for the run as a whole and stands above them
    whatever is picked. ``live`` says whether the choices take a gesture, which a conversion under
    way answers.
    """

    slots: Tuple[SettingsSlotViewModel, ...]
    inspected: Optional[InspectedSourceViewModel]
    drive: float
    live: bool

    @property
    def inspecting(self) -> bool:
        """A row is picked out, so the card has something to draw its choices on."""
        return self.inspected is not None
