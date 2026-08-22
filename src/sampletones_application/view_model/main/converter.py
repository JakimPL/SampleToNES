from enum import StrEnum
from pathlib import Path
from typing import Final, FrozenSet, Optional, Tuple

from pydantic import BaseModel

from sampletones_application.view_model.shared.percent import format_percent
from sampletones_application.view_model.shared.stems import (
    StemRowViewModel,
    StemsListViewModel,
)
from sampletones_core.constants.enums import ChannelName, HierarchyMode


class ConversionPhase(StrEnum):
    IDLE = "idle"
    WAITING = "waiting"
    RUNNING = "running"
    CANCELLING = "cancelling"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class ConverterAction(StrEnum):
    """The single action the panel's button offers in the current phase.

    Every terminal phase returns to idle on its own, so the button only ever
    starts a conversion or cancels the running one.
    """

    CONVERT = "convert"
    CANCEL = "cancel"


ACTIVE_PHASES: Final[FrozenSet[ConversionPhase]] = frozenset(
    {
        ConversionPhase.WAITING,
        ConversionPhase.RUNNING,
        ConversionPhase.CANCELLING,
    }
)


class ConverterViewModel(BaseModel, frozen=True):
    """
    An immutable snapshot of converter state that defines what the panel is allowed to know.

    Derived UI flags are computed properties, not stored fields — the phase is
    the single source of truth and the view model is always self-consistent by
    construction.
    """

    phase: ConversionPhase
    status_text: str
    action_label: str
    progress: float
    input_path: Optional[Path]
    output_path: Optional[Path]
    is_file: bool
    other_operation_active: bool
    stems_mode: bool
    stem_sources: Tuple[StemRowViewModel, ...]
    enabled_channels: FrozenSet[ChannelName]
    channel_cap: int
    max_channel_cap: int
    hierarchy_mode: HierarchyMode
    max_sources: int

    @property
    def progress_overlay(self) -> str:
        """The percentage label rendered over the progress bar, derived from the fraction."""
        return format_percent(self.progress)

    @property
    def is_active(self) -> bool:
        return self.phase in ACTIVE_PHASES

    @property
    def subpanel_visible(self) -> bool:
        return self.phase != ConversionPhase.IDLE

    @property
    def has_input(self) -> bool:
        """Something is there to convert: a listed recording holding a channel, or a selected path."""
        if self.stems_mode:
            return any(row.takes_part for row in self.stem_sources)

        return self.input_path is not None

    @property
    def source_count(self) -> int:
        return len(self.stem_sources)

    @property
    def channels_in_play(self) -> Tuple[ChannelName, ...]:
        """The channels a conversion may reach, in the order the application names them.

        A stems row offers a checkbox per channel in play, so a channel the configuration leaves
        out costs the row no column at all.
        """
        return tuple(channel_name for channel_name in ChannelName.items() if channel_name in self.enabled_channels)

    @property
    def stems_list(self) -> StemsListViewModel:
        """The gathered recordings as the stems list draws them, inert while a conversion runs."""
        return StemsListViewModel(
            rows=self.stem_sources,
            channels_in_play=self.channels_in_play,
            live=not self.is_active,
        )

    @property
    def level_count(self) -> int:
        """How many levels the gathered recordings are spread over."""
        return max((row.level + 1 for row in self.stem_sources), default=0)

    @property
    def playing_count(self) -> int:
        """How many of the listed recordings take part in the conversion."""
        return sum(1 for row in self.stem_sources if row.takes_part)

    @property
    def can_add_source(self) -> bool:
        """The list has room for another recording."""
        return self.source_count < self.max_sources

    @property
    def convert_button_enabled(self) -> bool:
        return self.phase == ConversionPhase.IDLE and self.has_input and not self.other_operation_active

    @property
    def primary_action(self) -> ConverterAction:
        """Cancel while a conversion occupies resources, otherwise convert.

        Terminal phases resolve back to idle on their own, so they present the
        convert action (disabled until the phase is actually idle)."""
        return ConverterAction.CANCEL if self.is_active else ConverterAction.CONVERT

    @property
    def primary_action_enabled(self) -> bool:
        if self.primary_action == ConverterAction.CANCEL:
            return self.phase != ConversionPhase.CANCELLING

        return self.convert_button_enabled
