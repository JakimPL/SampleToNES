from typing import Dict, Final, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.general.colors.text import TextColors
from sampletones_application.layout.settings import SettingsLayout
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import TAG_GLOBAL_THEME_DANGER_BUTTON
from sampletones_application.tags.settings import (
    TAG_SETTINGS_EXPORT_BUTTON_CANCEL,
    TAG_SETTINGS_EXPORT_GROUP_MEASURED,
    TAG_SETTINGS_EXPORT_GROUP_STAGES,
    TAG_SETTINGS_EXPORT_GROUP_WORKING,
    TAG_SETTINGS_EXPORT_PROGRESS,
    TAG_SETTINGS_EXPORT_TEXT_FIGURE,
    TAG_SETTINGS_EXPORT_TEXT_STAGE,
    TAG_SETTINGS_EXPORT_WINDOW,
)
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.layout.centered import centered
from sampletones_application.ui.elements.seeded import GUISeededDialogWindow
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.gui.dialog_navigation import FocusStop
from sampletones_application.utils.gui.dpg import dpg_configure_item, dpg_set_value
from sampletones_application.utils.gui.keyboard import KeyRouter
from sampletones_application.utils.gui.palette.dpg import dpg_set_palette_color
from sampletones_application.utils.gui.shortcuts.source import ShortcutSource
from sampletones_application.utils.palette.colors.base import BaseColor
from sampletones_application.view_model.shared.export import SongExportViewModel
from sampletones_core.exports.stage import ExportStage
from sampletones_shared.types.callback import VoidCallback

RING_STYLE: Final[int] = 1


class GUIExportWindow(GUISeededDialogWindow[SongExportViewModel]):
    """Modal report over an export while it runs.

    The file itself was named in the system's own save dialog, so this window has one face: what
    the run is doing. The stages appear as the format reaches them, the one under way sitting at
    the foot of the list, and it carries either a bar filling toward its end or the turning
    indicator of work whose length the data decides.

    Canceling is offered for as long as the run can still answer one.
    """

    def __init__(
        self,
        *,
        layout: SettingsLayout,
        text_colors: TextColors,
        language_manager: LanguageManager,
        key_router: KeyRouter,
        shortcut_source: ShortcutSource,
    ) -> None:
        self._language_manager = language_manager
        self._text_colors = text_colors
        self._indicator = layout.export.indicator

        self.on_cancel: Optional[VoidCallback] = None

        self._stage_labels: Dict[ExportStage, str] = {
            ExportStage.WALKING: language_manager["settings.export.label.stage_walking"],
            ExportStage.COMPRESSING: language_manager["settings.export.label.stage_compressing"],
            ExportStage.WRITING: language_manager["settings.export.label.stage_writing"],
        }

        super().__init__(
            tag=TAG_SETTINGS_EXPORT_WINDOW,
            geometry=layout.export.window,
            subject="export",
            key_router=key_router,
            shortcut_source=shortcut_source,
        )

    def create_window(self) -> None:
        with self.dialog_window(
            label=self._language_manager["settings.export.title.window_title"],
            on_close=None,
        ):
            self._create_stages()
            self._create_measured()
            self._create_working()
            dpg.add_separator()
            self._create_cancel()

        self._render()
        self._install_navigation(
            [
                FocusStop.button(
                    TAG_SETTINGS_EXPORT_BUTTON_CANCEL,
                    self._request_cancel,
                )
            ],
            on_escape=self._request_cancel,
        )

    def _create_stages(self) -> None:
        with dpg.group(tag=TAG_SETTINGS_EXPORT_GROUP_STAGES):
            for stage in ExportStage:
                tag = self._stage_tag(stage)
                dpg.add_text(
                    self._stage_labels[stage],
                    tag=tag,
                    show=False,
                )
                FontRegistry.bind_to_item(tag, Font.REGULAR)

    def _create_measured(self) -> None:
        with dpg.group(
            tag=TAG_SETTINGS_EXPORT_GROUP_MEASURED,
            show=False,
        ):
            dpg.add_progress_bar(
                tag=TAG_SETTINGS_EXPORT_PROGRESS,
                default_value=0.0,
                width=-1,
            )
            FontRegistry.bind_to_item(
                TAG_SETTINGS_EXPORT_PROGRESS,
                Font.MONO,
            )

    def _create_working(self) -> None:
        """The reading of a stage whose length the data decides: what it holds, and that it turns.

        A bar would have to state a fraction of something, and this stage travels toward nothing,
        so what stands here is the figure it does know beside a symbol that keeps moving. The pair
        stands centered in the window, and both are drawn in the figure's font, which is the font
        the ring takes its size from, so the ring sits level with the line beside it.
        """
        with (
            dpg.group(
                tag=TAG_SETTINGS_EXPORT_GROUP_WORKING,
                show=False,
            ),
            centered(),
            dpg.group(horizontal=True),
        ):
            dpg.add_loading_indicator(
                style=RING_STYLE,
                radius=self._indicator.radius,
                thickness=self._indicator.thickness,
            )
            dpg.add_text("", tag=TAG_SETTINGS_EXPORT_TEXT_FIGURE)

        FontRegistry.bind_to_item(
            TAG_SETTINGS_EXPORT_GROUP_WORKING,
            Font.MONO_SMALL,
        )

    def _create_cancel(self) -> None:
        GUIButton(
            tag=TAG_SETTINGS_EXPORT_BUTTON_CANCEL,
            label=self._language_manager["global.dialog.label.cancel"],
            callback=self._request_cancel,
            width=-1,
            theme=ThemeRegistry.get(TAG_GLOBAL_THEME_DANGER_BUTTON),
        )

    def _render(self) -> None:
        """Draws the run as it stands: what it has been through, and where the latest stage is."""
        view_model = self.view_model
        self._render_stages(view_model)
        dpg_configure_item(
            TAG_SETTINGS_EXPORT_GROUP_MEASURED,
            show=view_model.progress_visible,
        )
        dpg_set_value(TAG_SETTINGS_EXPORT_PROGRESS, view_model.progress)
        dpg_configure_item(
            TAG_SETTINGS_EXPORT_PROGRESS,
            overlay=view_model.progress_overlay,
        )
        dpg_configure_item(
            TAG_SETTINGS_EXPORT_GROUP_WORKING,
            show=view_model.working_visible,
        )
        dpg_set_value(TAG_SETTINGS_EXPORT_TEXT_FIGURE, view_model.figure)
        dpg_configure_item(
            TAG_SETTINGS_EXPORT_TEXT_FIGURE,
            show=view_model.figure_visible,
        )
        dpg_configure_item(
            TAG_SETTINGS_EXPORT_BUTTON_CANCEL,
            enabled=view_model.cancel_enabled,
        )

    def _render_stages(self, view_model: SongExportViewModel) -> None:
        """Lists what the run has reached, the stage under way reading ahead of the ones behind."""
        for stage in ExportStage:
            tag = self._stage_tag(stage)
            dpg_configure_item(tag, show=view_model.stage_visible(stage))
            dpg_set_palette_color(tag, self._stage_color(view_model, stage))

    def _stage_color(
        self,
        view_model: SongExportViewModel,
        stage: ExportStage,
    ) -> BaseColor:
        if view_model.stage_reached(stage):
            return self._text_colors.disabled

        return self._text_colors.default

    def _stage_tag(self, stage: ExportStage) -> str:
        return compose_tag(TAG_SETTINGS_EXPORT_TEXT_STAGE, stage.value)

    def _request_cancel(self) -> None:
        if self.view_model.cancel_enabled:
            self.call(self.on_cancel)
