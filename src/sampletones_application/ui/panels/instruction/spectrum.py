from typing import Any

from sampletones_application.categories.elements.instructions import (
    InstructionPanelElements,
)
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.constants.instructions import (
    TAG_INSTRUCTIONS_INSTRUCTION_PANEL_SPECTRUM,
    TAG_INSTRUCTIONS_SPECTRUM_PANEL,
)
from sampletones_application.layout.graphs import GraphsLayout
from sampletones_application.ui.elements.graphs.spectrum import GUISpectrumGraph
from sampletones_application.ui.elements.layout.card import card
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_core.library import InstructionLibraryFragment


class GUIInstructionSpectrumPanel(GUIPanel):
    def __init__(
        self,
        *,
        layout: GraphsLayout,
        language_manager: LanguageManager,
        status_bar: GUIStatusBar,
    ) -> None:
        self._layout = layout
        self._language_manager = language_manager
        self._status_bar = status_bar
        self.display: GUISpectrumGraph

        self._lbl_spectrum = language_manager[
            Page.INSTRUCTIONS,
            Panel.INSTRUCTION,
            TextType.LABEL,
            InstructionPanelElements.SPECTRUM_LABEL,
        ]

        super().__init__(
            tag=TAG_INSTRUCTIONS_SPECTRUM_PANEL,
        )

    def create_panel(self, parent: str) -> None:
        with card(parent, self.tag, width=0, no_scrollbar=True):
            self._create_section_header(
                self._lbl_spectrum,
                glyph=self._glyphs.headers.spectrum,
            )
            self.display = GUISpectrumGraph(
                tag=TAG_INSTRUCTIONS_INSTRUCTION_PANEL_SPECTRUM,
                parent=self.tag,
                layout=self._layout,
                language_manager=self._language_manager,
                status_bar=self._status_bar,
            )

    def load_library_fragment(
        self,
        fragment: InstructionLibraryFragment[Any],
        sample_rate: int,
        frame_length: int,
    ) -> None:
        self.display.load_library_fragment(fragment, sample_rate, frame_length)

    def clear_layers(self) -> None:
        self.display.clear_layers()
