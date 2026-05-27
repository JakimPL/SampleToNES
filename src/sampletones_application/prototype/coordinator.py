from pathlib import Path

import dearpygui.dearpygui as dpg

from sampletones_application.prototype.config.loader import load_prototype_config
from sampletones_application.prototype.constants.application import TAG_GROUP_TOP_PANELS, TAG_WINDOW_PROTOTYPE
from sampletones_application.prototype.logic.label_validation import LabelValidationLogic
from sampletones_application.prototype.logic.score import ScoreLogic
from sampletones_application.prototype.panels.label_input_panel import LabelInputPanel
from sampletones_application.prototype.panels.multiplier_panel import MultiplierPanel
from sampletones_application.prototype.panels.result_panel import ResultPanel
from sampletones_application.prototype.text.elements import PrototypePageElements
from sampletones_application.text.hierarchy import Page, Panel, TextType
from sampletones_application.text.key import TextKey
from sampletones_application.text.manager import LanguageManager

_KEY_WINDOW_TITLE = TextKey(Page.PROTOTYPE, Panel.PAGE, TextType.TITLE, PrototypePageElements.WINDOW_TITLE)

_CONFIG_PATH = Path(__file__).parent / "data" / "prototype.yaml"
_LANGUAGE_PATH = Path(__file__).parent / "data" / "en.yaml"


class PrototypeWindowCoordinator:
    def __init__(self) -> None:
        config = load_prototype_config(_CONFIG_PATH)
        self._lang = LanguageManager(_LANGUAGE_PATH)
        self._viewport_width = config.layout.viewport.width
        self._viewport_height = config.layout.viewport.height

        self._label_validation_logic = LabelValidationLogic(
            lang=self._lang,
            constraints=config.constraints.label_input,
        )
        self._score_logic = ScoreLogic(
            default_multiplier=config.constraints.multiplier.default_value,
        )

        self._label_panel = LabelInputPanel(
            TAG_GROUP_TOP_PANELS,
            lang=self._lang,
            layout=config.layout.label_input,
            constraints=config.constraints.label_input,
            on_label_changed=self._on_label_changed,
        )
        self._multiplier_panel = MultiplierPanel(
            TAG_GROUP_TOP_PANELS,
            lang=self._lang,
            layout=config.layout.multiplier,
            constraints=config.constraints.multiplier,
            on_multiplier_changed=self._score_logic.update_multiplier,
        )
        self._result_panel = ResultPanel(
            TAG_WINDOW_PROTOTYPE,
            lang=self._lang,
            layout=config.layout.result,
        )

        self._label_validation_logic.on_validation_changed = self._label_panel.update_validation
        self._score_logic.on_result = self._result_panel.update_view

    def _on_label_changed(self, label: str) -> None:
        self._label_validation_logic.update(label)
        self._score_logic.update_label(label)

    def run(self) -> None:
        dpg.create_context()
        dpg.create_viewport(
            title=self._lang[_KEY_WINDOW_TITLE],
            width=self._viewport_width,
            height=self._viewport_height,
        )
        dpg.setup_dearpygui()
        dpg.show_viewport()

        self._build_layout()

        dpg.set_primary_window(TAG_WINDOW_PROTOTYPE, True)

        while dpg.is_dearpygui_running():
            dpg.render_dearpygui_frame()

        dpg.destroy_context()

    def _build_layout(self) -> None:
        with dpg.window(tag=TAG_WINDOW_PROTOTYPE, no_title_bar=True, no_scrollbar=True):
            dpg.add_group(tag=TAG_GROUP_TOP_PANELS, horizontal=True)

        self._label_panel.create_panel()
        self._multiplier_panel.create_panel()
        self._result_panel.create_panel()
