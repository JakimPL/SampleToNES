from pathlib import Path
from typing import Final, FrozenSet, Optional, Tuple

import pytest

from sampletones_application.constants.conversion import MAX_STEM_SOURCES
from sampletones_application.view_model.main.converter import (
    ConversionPhase,
    ConverterAction,
    ConverterViewModel,
    StemSourceRow,
)
from sampletones_core.constants.enums import ChannelName, HierarchyMode

ENABLED_CHANNELS: Final[FrozenSet[ChannelName]] = frozenset(
    {ChannelName.PULSE1, ChannelName.TRIANGLE, ChannelName.NOISE}
)


def _row(
    name: str,
    *,
    channels: FrozenSet[ChannelName] = ENABLED_CHANNELS,
    level: int = 0,
    position: int = 0,
    level_size: int = 1,
    level_count: int = 1,
) -> StemSourceRow:
    return StemSourceRow(
        path=Path(f"/audio/{name}.wav"),
        channels=channels,
        level=level,
        position=position,
        level_size=level_size,
        level_count=level_count,
    )


def _view_model(
    *,
    phase: ConversionPhase,
    other_operation_active: bool = False,
    progress: float = 0.0,
    input_path: Optional[Path] = Path("/audio/sample.wav"),
    stems_mode: bool = False,
    stem_sources: Tuple[StemSourceRow, ...] = (),
    channel_cap: int = len(ENABLED_CHANNELS),
    max_sources: int = MAX_STEM_SOURCES,
) -> ConverterViewModel:
    return ConverterViewModel(
        phase=phase,
        status_text="",
        action_label="",
        progress=progress,
        input_path=input_path,
        output_path=Path("/reconstructions"),
        is_file=True,
        other_operation_active=other_operation_active,
        stems_mode=stems_mode,
        stem_sources=stem_sources,
        enabled_channels=ENABLED_CHANNELS,
        channel_cap=channel_cap,
        max_channel_cap=len(ENABLED_CHANNELS),
        hierarchy_mode=HierarchyMode.ROUND_ROBIN,
        max_sources=max_sources,
    )


class TestConvertButtonGating:
    """An input is loaded and the converter is idle, so the only thing that should withhold the Convert
    button is another exclusive operation (a library generating elsewhere)."""

    def test_enabled_when_no_other_operation_active(self) -> None:
        view_model = _view_model(phase=ConversionPhase.IDLE, other_operation_active=False)
        assert view_model.convert_button_enabled is True

    def test_disabled_while_another_operation_is_active(self) -> None:
        view_model = _view_model(phase=ConversionPhase.IDLE, other_operation_active=True)
        assert view_model.convert_button_enabled is False


class TestProgressOverlay:
    """The overlay label is a projection of the progress fraction, clamped to the bar's range,
    so a full bar always reads 100% and the label can never disagree with the fill."""

    @pytest.mark.parametrize(
        ("progress", "overlay"),
        [
            (-0.5, "0%"),
            (0.0, "0%"),
            (0.333, "33%"),
            (0.5, "50%"),
            (1.0, "100%"),
            (1.5, "100%"),
        ],
    )
    def test_overlay_renders_the_clamped_percentage(self, progress: float, overlay: str) -> None:
        view_model = _view_model(phase=ConversionPhase.RUNNING, progress=progress)
        assert view_model.progress_overlay == overlay


class TestPrimaryAction:
    """The one action button cancels while a conversion holds resources and otherwise offers to
    convert; terminal phases present the convert action as they fall back to idle on their own.
    """

    @pytest.mark.parametrize(
        ("phase", "action"),
        [
            (ConversionPhase.IDLE, ConverterAction.CONVERT),
            (ConversionPhase.WAITING, ConverterAction.CANCEL),
            (ConversionPhase.RUNNING, ConverterAction.CANCEL),
            (ConversionPhase.CANCELLING, ConverterAction.CANCEL),
            (ConversionPhase.COMPLETED, ConverterAction.CONVERT),
            (ConversionPhase.CANCELLED, ConverterAction.CONVERT),
            (ConversionPhase.FAILED, ConverterAction.CONVERT),
        ],
    )
    def test_action_follows_phase(self, phase: ConversionPhase, action: ConverterAction) -> None:
        assert _view_model(phase=phase).primary_action == action


class TestPrimaryActionEnabled:
    """Cancel stays live while running but is withheld once the stop is already in flight; convert
    is live only from an idle panel that has an input selected."""

    @pytest.mark.parametrize(
        ("phase", "enabled"),
        [
            (ConversionPhase.WAITING, True),
            (ConversionPhase.RUNNING, True),
            (ConversionPhase.CANCELLING, False),
        ],
    )
    def test_cancel_enablement(self, phase: ConversionPhase, enabled: bool) -> None:
        assert _view_model(phase=phase).primary_action_enabled is enabled

    @pytest.mark.parametrize(
        "phase",
        [ConversionPhase.COMPLETED, ConversionPhase.CANCELLED, ConversionPhase.FAILED],
    )
    def test_convert_disabled_in_terminal_phases(self, phase: ConversionPhase) -> None:
        assert _view_model(phase=phase).primary_action_enabled is False

    def test_convert_enabled_when_idle_with_input(self) -> None:
        assert _view_model(phase=ConversionPhase.IDLE).primary_action_enabled is True


class TestStemsSection:
    """In stems mode the listed recordings are what there is to convert, and the list has a bound."""

    def test_a_listed_recording_counts_as_an_input(self) -> None:
        view_model = _view_model(
            phase=ConversionPhase.IDLE,
            input_path=None,
            stems_mode=True,
            stem_sources=(_row("bass"),),
        )

        assert view_model.has_input is True
        assert view_model.source_count == 1
        assert view_model.convert_button_enabled is True

    def test_an_empty_list_offers_nothing_to_convert(self) -> None:
        view_model = _view_model(phase=ConversionPhase.IDLE, stems_mode=True)

        assert view_model.has_input is False
        assert view_model.convert_button_enabled is False

    def test_the_selected_path_carries_a_classic_conversion(self) -> None:
        view_model = _view_model(phase=ConversionPhase.IDLE, stems_mode=False)

        assert view_model.has_input is True

    def test_a_full_list_takes_no_more(self) -> None:
        rows = tuple(_row(str(index)) for index in range(MAX_STEM_SOURCES))
        view_model = _view_model(phase=ConversionPhase.IDLE, stems_mode=True, stem_sources=rows)

        assert view_model.can_add_source is False

    def test_a_list_with_room_takes_another(self) -> None:
        view_model = _view_model(phase=ConversionPhase.IDLE, stems_mode=True, stem_sources=(_row("bass"),))

        assert view_model.can_add_source is True

    def test_a_row_names_itself_by_its_file(self) -> None:
        assert _row("bass").name == "bass.wav"

    def test_a_row_holding_no_channel_offers_nothing_to_convert(self) -> None:
        view_model = _view_model(
            phase=ConversionPhase.IDLE,
            input_path=None,
            stems_mode=True,
            stem_sources=(_row("bass", channels=frozenset()),),
        )

        assert view_model.has_input is False
        assert view_model.playing_count == 0
        assert view_model.convert_button_enabled is False


class TestRowStanding:
    """A row states where it stands, so the moves it offers grey themselves out from the row alone."""

    def test_the_only_row_of_the_only_level_can_go_nowhere(self) -> None:
        row = _row("bass")

        assert row.is_first_on_level is True
        assert row.is_last_on_level is True
        assert row.alone_on_level is True
        assert row.has_level_above is False
        assert row.has_level_below is False

    def test_a_row_between_levels_can_join_either(self) -> None:
        row = _row("lead", level=1, level_count=3)

        assert row.has_level_above is True
        assert row.has_level_below is True

    def test_a_row_sharing_a_level_names_its_place_among_its_peers(self) -> None:
        row = _row("lead", position=1, level_size=3)

        assert row.is_first_on_level is False
        assert row.is_last_on_level is False
        assert row.alone_on_level is False
