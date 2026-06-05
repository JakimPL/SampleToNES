import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.sequencer import SequencerInstrumentsElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.constants.general import (
    SUF_PANEL_RIGHT,
    TAG_GLOBAL_TAB_SEQUENCER,
)
from sampletones_application.constants.sequencer import (
    TAG_SEQUENCER_INSTRUMENTS_PANEL,
    TAG_SEQUENCER_INSTRUMENTS_TABLE,
    TAG_SEQUENCER_INSTRUMENTS_WINDOW,
)
from sampletones_application.layout.sequencer import SequencerLayout
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.panel import GUIPanel


class GUISequencerSamplesPanel(GUIPanel):
    def __init__(
        self,
        *,
        layout: SequencerLayout,
        language_manager: LanguageManager,
    ) -> None:
        self._layout = layout
        self._lbl_instruments = language_manager[
            Page.SEQUENCER,
            Panel.INSTRUMENTS,
            TextType.LABEL,
            SequencerInstrumentsElements.INSTRUMENTS_TEXT,
        ]
        self._lbl_column_id = language_manager[
            Page.SEQUENCER,
            Panel.INSTRUMENTS,
            TextType.LABEL,
            SequencerInstrumentsElements.COLUMN_ID,
        ]
        self._lbl_column_name = language_manager[
            Page.SEQUENCER,
            Panel.INSTRUMENTS,
            TextType.LABEL,
            SequencerInstrumentsElements.COLUMN_NAME,
        ]

        super().__init__(
            tag=TAG_SEQUENCER_INSTRUMENTS_PANEL,
            parent=f"{TAG_GLOBAL_TAB_SEQUENCER}{SUF_PANEL_RIGHT}",
            width=-1,
            height=-1,
        )

    def create_panel(self) -> None:
        with dpg.child_window(
            tag=self.tag,
            width=self.width,
            height=self.height,
            parent=self.parent,
            border=False,
        ):
            self._create_section_text()
            self._create_samples_table()

    def _create_section_text(self) -> None:
        section_text = dpg.add_text(self._lbl_instruments)
        FontRegistry.bind_to_item(section_text, Font.BOLD)

    def _create_samples_table(self) -> None:
        dpg.add_separator()
        with dpg.child_window(
            tag=TAG_SEQUENCER_INSTRUMENTS_WINDOW,
            border=False,
            width=-1,
            height=-1,
        ):
            with dpg.table(
                tag=TAG_SEQUENCER_INSTRUMENTS_TABLE,
                width=-1,
                height=-1,
                header_row=True,
                resizable=False,
                borders_innerH=False,
                borders_innerV=True,
                borders_outerH=True,
                borders_outerV=True,
                scrollY=True,
                policy=dpg.mvTable_SizingFixedFit,
            ):
                dpg.add_table_column(
                    label=self._lbl_column_id,
                    width_fixed=True,
                    init_width_or_weight=self._layout.table_cells.instrument_id,
                )
                dpg.add_table_column(
                    label=self._lbl_column_name,
                    init_width_or_weight=self._layout.table_cells.instrument_name,
                )
