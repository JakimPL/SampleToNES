from typing import Final, FrozenSet, Optional, Tuple

from pydantic import BaseModel

from sampletones_application.constants.sources import SourceKind
from sampletones_application.view_model.shared.agreement import Agreement
from sampletones_core.constants.algorithm import (
    ALL_STEMS_CHANNEL_CAP,
    MIN_STEMS_CHANNEL_CAP,
    UNIT_DRIVE,
)
from sampletones_core.constants.enums import TONE_CHANNELS, ChannelName

CHANNEL_CAP_STEPS: Final[Tuple[int, ...]] = tuple(range(MIN_STEMS_CHANNEL_CAP, ALL_STEMS_CHANNEL_CAP + 1))


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


class ChannelSettingsViewModel(BaseModel, frozen=True):
    """One channel as the settings card draws it: its use, its bend and how hard it is driven.

    ``use`` and ``bend`` read the way a folder's boxes do — every inspected recording makes the
    choice, some of them do, or none does. ``drive`` is the level they agree on, and nothing where
    they differ.
    """

    channel: ChannelName
    use: Agreement
    bend: Agreement
    drive: Optional[float]

    @property
    def used(self) -> bool:
        """An inspected recording occupies the channel, which is what its bend and its drive belong to."""
        return self.use is not Agreement.NONE

    @property
    def bendable(self) -> bool:
        """The channel's hardware loads a divider, which is what puts a box in the bend column."""
        return self.channel in TONE_CHANNELS

    @property
    def bend_offered(self) -> bool:
        """A bend is put to a reader here: the hardware reads one and a recording occupies it."""
        return self.bendable and self.used

    @property
    def drive_mixed(self) -> bool:
        """The recordings the card inspects drive the channel differently."""
        return self.drive is None

    @property
    def drive_shown(self) -> float:
        """Where the channel's slider rests, unit drive standing for a mixed reading."""
        return UNIT_DRIVE if self.drive is None else self.drive


class SourceSettingsPanelViewModel(BaseModel, frozen=True):
    """What the settings card shows: one line per channel, and the row it edits them on.

    ``subject`` names the row a reader picked out of the converter's list; with none picked the
    card edits the settings a recording joins with, which is what every recording gathered from
    then on starts with. ``caps`` are the counts the inspected recordings hold, so a folder whose
    recordings differ reads half-lit, and ``channels_used`` is the most channels any of them
    occupies, past which a step reaches nothing. ``live`` says whether the card takes a gesture,
    which a conversion under way answers.
    """

    subject: Optional[InspectedSourceViewModel]
    channels: Tuple[ChannelSettingsViewModel, ...]
    caps: FrozenSet[int]
    channels_used: int
    live: bool

    @property
    def edits_new_recordings(self) -> bool:
        """No row is picked out, so the card edits what a recording joins with."""
        return self.subject is None

    @property
    def channel_cap(self) -> Optional[int]:
        """The count the inspected recordings agree on, and nothing where they differ."""
        return next(iter(self.caps)) if len(self.caps) == 1 else None

    def step_agreement(self, step: int) -> Agreement:
        """How the inspected recordings read on one step of the count."""
        if self.caps == {step}:
            return Agreement.ALL

        return Agreement.SOME if step in self.caps else Agreement.NONE

    def step_reaches(self, step: int) -> bool:
        """A run could sound this many channels, which the channels a recording occupies allow."""
        return step <= self.channels_used
