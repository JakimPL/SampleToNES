from typing import Callable, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.general.inputs import InputsLayout
from sampletones_application.layout.tabs.main.source import SourceSettingsLayout
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import (
    SUF_BUTTON,
    SUF_TOOLTIP,
    TAG_GLOBAL_THEME_STEP_BUTTON,
    TAG_GLOBAL_THEME_STEP_BUTTON_DIM,
    TAG_GLOBAL_THEME_STEP_BUTTON_LIT,
    TAG_GLOBAL_THEME_STEP_BUTTON_PARTIAL,
)
from sampletones_application.tags.main import PRE_MAIN_SOURCE_STEP, TAG_MAIN_SOURCE_GROUP_STEPS
from sampletones_application.ui.elements.field import labeled_field
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.gui.dpg import dpg_configure_item
from sampletones_application.utils.gui.tooltip import show_tooltip
from sampletones_application.view_model.main.source import CHANNEL_CAP_STEPS, SourceSettingsPanelViewModel
from sampletones_application.view_model.shared.agreement import Agreement
from sampletones_shared.types.application import Sender
from sampletones_shared.utils.callbacks import CallbackMixin

StepCallback = Callable[[int], None]


class ChannelCapSteps(CallbackMixin):
    """How many channels a recording may sound at once, as a row of steps from one to them all.

    The count a recording holds lights its step, and a folder whose recordings differ half-lights
    every count present. A step past the channels any inspected recording uses reads dim, since
    a run sounds at most the channels a recording holds; it still takes the gesture, so a count
    set ahead of the channels stands once they are added.
    """

    def __init__(
        self,
        *,
        layout: SourceSettingsLayout,
        inputs: InputsLayout,
        language_manager: LanguageManager,
        status_bar: GUIStatusBar,
    ) -> None:
        self._layout = layout
        self._label_width = inputs.label_width
        self._status_bar = status_bar
        self._lbl_channel_cap = language_manager["main.source.label.channel_cap"]
        self._msg_channel_cap = language_manager["main.source.tooltip.tooltip_channel_cap"]
        self._tpl_status = language_manager["main.source.message.status_channel_cap"]

        self.on_channel_cap_changed: Optional[StepCallback] = None

    @staticmethod
    def step_tag(step: int) -> str:
        return compose_tag(PRE_MAIN_SOURCE_STEP, str(step), SUF_BUTTON)

    def create(self) -> None:
        """Build the steps beside the name of the choice they make."""
        with (
            labeled_field(self._lbl_channel_cap, self._label_width),
            dpg.group(tag=TAG_MAIN_SOURCE_GROUP_STEPS, horizontal=True),
        ):
            for step in CHANNEL_CAP_STEPS:
                self._create_step(step)

    def render(self, view_model: SourceSettingsPanelViewModel) -> None:
        """Light the counts the inspected recordings hold, dimming the ones their channels leave unreached."""
        for step in CHANNEL_CAP_STEPS:
            step_tag = self.step_tag(step)
            dpg_configure_item(step_tag, enabled=view_model.live)
            ThemeRegistry.get(self._step_theme(view_model, step)).bind_to_item(step_tag)

    def _create_step(self, step: int) -> None:
        step_tag = self.step_tag(step)
        dpg.add_button(
            label=str(step),
            tag=step_tag,
            width=self._layout.step_button_width,
            user_data=step,
            callback=self._on_step,
        )
        FontRegistry.bind_to_item(step_tag, Font.MONO_SMALL)
        self._status_bar.bind_to_item(step_tag, self._tpl_status.format(count=step))
        show_tooltip(step_tag, self._msg_channel_cap, tag=compose_tag(step_tag, SUF_TOOLTIP))

    @staticmethod
    def _step_theme(view_model: SourceSettingsPanelViewModel, step: int) -> str:
        match view_model.step_agreement(step):
            case Agreement.ALL:
                return TAG_GLOBAL_THEME_STEP_BUTTON_LIT
            case Agreement.SOME:
                return TAG_GLOBAL_THEME_STEP_BUTTON_PARTIAL
            case _:
                return (
                    TAG_GLOBAL_THEME_STEP_BUTTON if view_model.step_reaches(step) else TAG_GLOBAL_THEME_STEP_BUTTON_DIM
                )

    def _on_step(self, _sender: Sender, _app_data: None, step: int) -> None:
        self.call(self.on_channel_cap_changed, step)
