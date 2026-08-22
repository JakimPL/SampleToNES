from typing import Final, Tuple

from sampletones_application.view_model.shared.export import (
    ExportPhase,
    SongExportViewModel,
)
from sampletones_core.exports.stage import ExportStage

HALFWAY: Final[float] = 0.5
NO_PROGRESS: Final[float] = 0.0
SIZE: Final[str] = "8761 of 32429 bytes"


def view_model(
    *,
    phase: ExportPhase = ExportPhase.EXPORTING,
    stages: Tuple[ExportStage, ...] = (ExportStage.WALKING,),
    figure: str = "",
    progress: float = HALFWAY,
    travelling: bool = True,
) -> SongExportViewModel:
    return SongExportViewModel(
        phase=phase,
        stages=stages,
        figure=figure,
        progress=progress,
        travelling=travelling,
    )


class TestWhatTheDialogOpensOn:
    """A window with no run behind it draws nothing and offers no stop."""

    def test_an_idle_dialog_lists_no_stage(self) -> None:
        assert SongExportViewModel.idle().stages == ()

    def test_an_idle_dialog_is_not_active(self) -> None:
        assert SongExportViewModel.idle().is_active is False

    def test_an_idle_dialog_offers_no_stop(self) -> None:
        assert SongExportViewModel.idle().cancel_enabled is False


class TestWhereTheRunStands:
    """The stage at the foot of the list is the one under way; the rest are behind it."""

    def test_the_last_stage_reached_is_the_one_under_way(self) -> None:
        reached = (ExportStage.WALKING, ExportStage.COMPRESSING)
        assert view_model(stages=reached).stage == ExportStage.COMPRESSING

    def test_a_run_that_has_named_nothing_has_no_stage_under_way(self) -> None:
        assert view_model(stages=()).stage is None

    def test_a_stage_the_run_has_left_reads_as_behind(self) -> None:
        reached = (ExportStage.WALKING, ExportStage.COMPRESSING)
        assert view_model(stages=reached).stage_reached(ExportStage.WALKING) is True

    def test_the_stage_under_way_does_not_read_as_behind(self) -> None:
        reached = (ExportStage.WALKING, ExportStage.COMPRESSING)
        assert view_model(stages=reached).stage_reached(ExportStage.COMPRESSING) is False

    def test_a_stage_the_run_never_reached_is_left_off_the_list(self) -> None:
        assert view_model().stage_visible(ExportStage.WRITING) is False


class TestHowTheStageUnderWayReads:
    """A stage arriving at an end carries a bar; one that does not carries the turning symbol."""

    def test_a_travelling_stage_shows_its_bar(self) -> None:
        assert view_model(travelling=True).progress_visible is True

    def test_a_travelling_stage_hides_the_turning_symbol(self) -> None:
        assert view_model(travelling=True).working_visible is False

    def test_a_stage_without_an_end_shows_the_turning_symbol(self) -> None:
        assert view_model(travelling=False, figure=SIZE).working_visible is True

    def test_a_bar_is_labelled_with_the_share_it_has_covered(self) -> None:
        assert view_model(progress=HALFWAY).progress_overlay == "50%"


class TestStoppingARun:
    """A stop is offered until it is taken."""

    def test_a_running_export_takes_a_stop(self) -> None:
        assert view_model(phase=ExportPhase.EXPORTING).cancel_enabled is True

    def test_an_export_already_stopping_takes_no_further_stop(self) -> None:
        assert view_model(phase=ExportPhase.CANCELLING).cancel_enabled is False

    def test_an_export_being_stopped_still_holds_the_screen(self) -> None:
        assert view_model(phase=ExportPhase.CANCELLING).is_active is True
