import dearpygui.dearpygui as dpg

from ...constants.general import SUF_PANEL_RIGHT, TAG_TAB_SEQUENCER
from ...constants.sequencer import (
    DIM_TABLE_CELL_WIDTH_SEQUENCER_INSTRUMENTS_ID,
    DIM_TABLE_CELL_WIDTH_SEQUENCER_INSTRUMENTS_NAME,
    LBL_TABLE_SEQUENCER_INSTRUMENTS_COLUMN_ID,
    LBL_TABLE_SEQUENCER_INSTRUMENTS_COLUMN_NAME,
    LBL_TEXT_SEQUENCER_INSTRUMENTS,
    TAG_PANEL_SEQUENCER_INSTRUMENTS,
    TAG_TABLE_SEQUENCER_INSTRUMENTS,
    TAG_WINDOW_SEQUENCER_INSTRUMENTS,
)
from ...elements.fonts.font import Font
from ...elements.fonts.registry import FontRegistry
from ...elements.panel import GUIPanel


class GUISequencerInstrumentsPanel(GUIPanel):
    def __init__(self) -> None:
        super().__init__(
            tag=TAG_PANEL_SEQUENCER_INSTRUMENTS,
            parent=f"{TAG_TAB_SEQUENCER}{SUF_PANEL_RIGHT}",
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
            self._create_instruments_table()

    def _create_section_text(self) -> None:
        section_text = dpg.add_text(LBL_TEXT_SEQUENCER_INSTRUMENTS)
        FontRegistry.bind_to_item(section_text, Font.BOLD)

    def _create_instruments_table(self) -> None:
        dpg.add_separator()
        with dpg.child_window(
            tag=TAG_WINDOW_SEQUENCER_INSTRUMENTS,
            border=False,
            width=-1,
            height=-1,
        ):
            with dpg.table(
                tag=TAG_TABLE_SEQUENCER_INSTRUMENTS,
                header_row=True,
                resizable=True,
                borders_innerH=False,
                borders_innerV=True,
                borders_outerH=True,
                borders_outerV=True,
                scrollY=True,
                policy=dpg.mvTable_SizingFixedFit,
            ):
                dpg.add_table_column(
                    label=LBL_TABLE_SEQUENCER_INSTRUMENTS_COLUMN_ID,
                    width_fixed=True,
                    init_width_or_weight=DIM_TABLE_CELL_WIDTH_SEQUENCER_INSTRUMENTS_ID,
                )
                dpg.add_table_column(
                    label=LBL_TABLE_SEQUENCER_INSTRUMENTS_COLUMN_NAME,
                    init_width_or_weight=DIM_TABLE_CELL_WIDTH_SEQUENCER_INSTRUMENTS_NAME,
                )
