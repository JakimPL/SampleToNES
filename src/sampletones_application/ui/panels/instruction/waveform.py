from typing import Any

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.graphs import GraphsLayout
from sampletones_application.tags.instructions import (
    TAG_INSTRUCTIONS_INSTRUCTION_PANEL_INSTRUCTION_WAVEFORM,
    TAG_INSTRUCTIONS_INSTRUCTION_PANEL_WAVEFORM,
)
from sampletones_application.ui.elements.graphs.waveform import GUIWaveformGraph
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_core.library import InstructionLibraryFragment


class GUIInstructionWaveformPanel(GUIPanel):
    def __init__(
        self,
        *,
        layout: GraphsLayout,
        language_manager: LanguageManager,
        status_bar: GUIStatusBar,
        initial_collapsed: bool = False,
    ) -> None:
        self._layout = layout
        self._language_manager = language_manager
        self._status_bar = status_bar
        self.display: GUIWaveformGraph

        super().__init__(
            tag=TAG_INSTRUCTIONS_INSTRUCTION_PANEL_WAVEFORM,
        )
        self._enable_vertical_collapse(
            initial_collapsed=initial_collapsed,
            auto_height=True,
        )

    def create_panel(self, parent: str) -> None:
        with self._collapsible_card(
            parent,
            self._language_manager["instructions.instruction.label.waveform_label"],
            glyph=self._glyphs.headers.waveform,
            width=0,
            no_scrollbar=True,
        ):
            self.display = GUIWaveformGraph(
                tag=TAG_INSTRUCTIONS_INSTRUCTION_PANEL_INSTRUCTION_WAVEFORM,
                parent=self._body_container,
                layout=self._layout,
                language_manager=self._language_manager,
                status_bar=self._status_bar,
            )

    def set_display_height(self, height: int) -> None:
        self.display.set_height(height)

    def load_library_fragment(
        self,
        fragment: InstructionLibraryFragment[Any],
    ) -> None:
        self.display.load_library_fragment(fragment)

    def clear_layers(self) -> None:
        self.display.clear_layers()

    def set_position(self, position: int) -> None:
        self.display.set_position(position)
