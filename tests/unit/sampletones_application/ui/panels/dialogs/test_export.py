from typing import Final, List, Tuple

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.config import LayoutConfig
from sampletones_application.paths import LANG_EN
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import SUF_BUTTON
from sampletones_application.tags.settings import (
    TAG_SETTINGS_EXPORT_BUTTON_CANCEL,
    TAG_SETTINGS_EXPORT_GROUP_MEASURED,
    TAG_SETTINGS_EXPORT_GROUP_WORKING,
    TAG_SETTINGS_EXPORT_PROGRESS,
    TAG_SETTINGS_EXPORT_TEXT_FIGURE,
    TAG_SETTINGS_EXPORT_TEXT_STAGE,
)
from sampletones_application.ui.panels.dialogs.export import GUIExportWindow
from sampletones_application.utils.gui.keyboard import KeyRouter
from sampletones_application.view_model.shared.export import (
    ExportPhase,
    SongExportViewModel,
)
from sampletones_core.exports.stage import ExportStage
from tests.suite.shortcuts import shipped_source

LANGUAGE_MANAGER: Final[LanguageManager] = LanguageManager(LANG_EN)
HALFWAY: Final[float] = 0.5
SIZE: Final[str] = "8761 of 32429 bytes"


@pytest.fixture(name="window")
def window_fixture(dpg_context: None, layout_config: LayoutConfig) -> GUIExportWindow:
    return GUIExportWindow(
        layout=layout_config.settings,
        text_colors=layout_config.general.colors.text,
        language_manager=LANGUAGE_MANAGER,
        key_router=KeyRouter(),
        shortcut_source=shipped_source(),
    )


def render(
    window: GUIExportWindow,
    *,
    stages: Tuple[ExportStage, ...] = (ExportStage.WALKING,),
    phase: ExportPhase = ExportPhase.EXPORTING,
    figure: str = "",
    progress: float = HALFWAY,
    travelling: bool = True,
) -> None:
    """Builds the widget tree and draws the given state, the way an open window is kept up to date."""
    window.create_window()
    window.update_view(
        SongExportViewModel(
            phase=phase,
            stages=stages,
            figure=figure,
            progress=progress,
            travelling=travelling,
        )
    )


def stage_tag(stage: ExportStage) -> str:
    return compose_tag(TAG_SETTINGS_EXPORT_TEXT_STAGE, stage.value)


def shown(tag: str) -> bool:
    return bool(dpg.get_item_configuration(tag)["show"])


class TestTheStageList:
    """A stage appears once the run has reached it, and stays as the run moves on."""

    def test_a_reached_stage_is_listed(self, window: GUIExportWindow) -> None:
        render(window, stages=(ExportStage.WALKING,))
        assert shown(stage_tag(ExportStage.WALKING))

    def test_a_stage_the_run_never_reached_is_left_off(self, window: GUIExportWindow) -> None:
        render(window, stages=(ExportStage.WALKING,))
        assert not shown(stage_tag(ExportStage.WRITING))

    def test_every_stage_reached_stays_on_the_list(self, window: GUIExportWindow) -> None:
        render(window, stages=(ExportStage.WALKING, ExportStage.COMPRESSING, ExportStage.WRITING))
        listed: List[ExportStage] = [stage for stage in ExportStage if shown(stage_tag(stage))]
        assert listed == [ExportStage.WALKING, ExportStage.COMPRESSING, ExportStage.WRITING]

    def test_the_reader_finds_each_stage_under_its_own_name(self, window: GUIExportWindow) -> None:
        render(window, stages=(ExportStage.COMPRESSING,))
        assert dpg.get_value(stage_tag(ExportStage.COMPRESSING)) == "Compressing the song"


class TestHowTheStageUnderWayReads:
    """A stage arriving at an end carries a bar; one measured against a limit carries a figure."""

    def test_a_travelling_stage_shows_its_bar(self, window: GUIExportWindow) -> None:
        render(window, travelling=True)
        assert shown(TAG_SETTINGS_EXPORT_GROUP_MEASURED)
        assert not shown(TAG_SETTINGS_EXPORT_GROUP_WORKING)

    def test_a_bar_stands_where_the_stage_has_reached(self, window: GUIExportWindow) -> None:
        render(window, travelling=True, progress=HALFWAY)
        assert dpg.get_value(TAG_SETTINGS_EXPORT_PROGRESS) == pytest.approx(HALFWAY)

    def test_a_bar_is_labelled_with_the_share_it_has_covered(self, window: GUIExportWindow) -> None:
        render(window, travelling=True, progress=HALFWAY)
        assert dpg.get_item_configuration(TAG_SETTINGS_EXPORT_PROGRESS)["overlay"] == "50%"

    def test_a_stage_without_an_end_shows_what_it_holds(self, window: GUIExportWindow) -> None:
        render(window, travelling=False, figure=SIZE)
        assert shown(TAG_SETTINGS_EXPORT_GROUP_WORKING)
        assert not shown(TAG_SETTINGS_EXPORT_GROUP_MEASURED)

    def test_the_figure_reaches_the_reader(self, window: GUIExportWindow) -> None:
        render(window, travelling=False, figure=SIZE)
        assert dpg.get_value(TAG_SETTINGS_EXPORT_TEXT_FIGURE) == SIZE


class TestStoppingARun:
    """Cancel stands while the run can still answer it, and reports the ask once."""

    def test_a_running_export_offers_a_stop(self, window: GUIExportWindow) -> None:
        render(window, phase=ExportPhase.EXPORTING)
        assert dpg.get_item_configuration(TAG_SETTINGS_EXPORT_BUTTON_CANCEL)["enabled"]

    def test_an_export_already_stopping_offers_no_further_stop(self, window: GUIExportWindow) -> None:
        render(window, phase=ExportPhase.CANCELLING)
        assert not dpg.get_item_configuration(TAG_SETTINGS_EXPORT_BUTTON_CANCEL)["enabled"]

    def test_pressing_cancel_asks_the_run_to_stop(self, window: GUIExportWindow) -> None:
        asked: List[bool] = []
        window.on_cancel = lambda: asked.append(True)
        render(window, phase=ExportPhase.EXPORTING)
        dpg.get_item_callback(compose_tag(TAG_SETTINGS_EXPORT_BUTTON_CANCEL, SUF_BUTTON))()
        assert asked == [True]

    def test_a_run_already_stopping_takes_no_second_ask(self, window: GUIExportWindow) -> None:
        asked: List[bool] = []
        window.on_cancel = lambda: asked.append(True)
        render(window, phase=ExportPhase.CANCELLING)
        dpg.get_item_callback(compose_tag(TAG_SETTINGS_EXPORT_BUTTON_CANCEL, SUF_BUTTON))()
        assert asked == []
