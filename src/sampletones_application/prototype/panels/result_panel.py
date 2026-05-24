import dearpygui.dearpygui as dpg

from sampletones_application.text.hierarchy import Page, Panel, TextType
from sampletones_application.text.key import TextKey
from sampletones_application.text.manager import LanguageManager

from ...elements.panel import GUIPanel
from ..config.layout import ResultLayout
from ..constants.result import (
    TAG_PANEL_PROTOTYPE_RESULT,
    TAG_TEXT_PROTOTYPE_RESULT,
    TAG_TEXT_PROTOTYPE_SCORE,
)
from ..models.score import ScoreResultViewModel
from ..text.elements import ResultElements

_KEY_SECTION = TextKey(Page.PROTOTYPE, Panel.RESULT, TextType.LABEL, ResultElements.SECTION_HEADER)
_KEY_NO_RESULT = TextKey(Page.PROTOTYPE, Panel.RESULT, TextType.MESSAGE, ResultElements.NO_RESULT)
_KEY_SCORE = TextKey(Page.PROTOTYPE, Panel.RESULT, TextType.MESSAGE, ResultElements.SCORE)


class ResultPanel(GUIPanel):
    def __init__(
        self,
        parent: str,
        *,
        lang: LanguageManager,
        layout: ResultLayout,
    ) -> None:
        self._lang = lang
        super().__init__(
            tag=TAG_PANEL_PROTOTYPE_RESULT,
            parent=parent,
            width=-1,
            height=layout.panel_height,
        )

    def create_panel(self) -> None:
        with dpg.child_window(
            tag=self.tag,
            parent=self.parent,
            width=self.width,
            height=self.height,
            border=True,
        ):
            dpg.add_text(self._lang[_KEY_SECTION])
            dpg.add_separator()
            dpg.add_text(tag=TAG_TEXT_PROTOTYPE_RESULT, default_value=self._lang[_KEY_NO_RESULT])
            dpg.add_text(tag=TAG_TEXT_PROTOTYPE_SCORE, default_value="")

    def update_view(self, view_model: ScoreResultViewModel) -> None:
        dpg.set_value(TAG_TEXT_PROTOTYPE_RESULT, view_model.result_text)
        dpg.set_value(TAG_TEXT_PROTOTYPE_SCORE, self._lang[_KEY_SCORE].format(view_model.score))
