from typing import Callable, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.sequencer import SequencerInstrumentsElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.constants.general import (
    SUF_HANDLER_REGISTRY,
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
from sampletones_application.view_model.sequencer.samples import SequencerSamplesViewModel
from sampletones_shared.types.application import Sender


class GUISequencerSamplesPanel(GUIPanel):
    def __init__(
        self,
        *,
        layout: SequencerLayout,
        language_manager: LanguageManager,
    ) -> None:
        self._layout = layout
        self._row_handler_tag = f"{TAG_SEQUENCER_INSTRUMENTS_TABLE}{SUF_HANDLER_REGISTRY}"
        self.on_sample_selected: Optional[Callable[[str], None]] = None
        self.on_sample_edit_requested: Optional[Callable[[str], None]] = None
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
        self._create_row_handlers()

    def _create_row_handlers(self) -> None:
        with dpg.item_handler_registry(tag=self._row_handler_tag):
            dpg.add_item_double_clicked_handler(callback=self._on_sample_double_clicked)

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

    def update_view(self, view_model: SequencerSamplesViewModel) -> None:
        """Rebuilds the samples table with explicit parents.

        Items pass an explicit ``parent`` rather than nesting ``with`` blocks: the
        browser tree builds on a worker thread and the DearPyGui container stack
        is process-global, so ``with`` blocks here would race with it.
        """
        dpg.delete_item(TAG_SEQUENCER_INSTRUMENTS_TABLE, children_only=True, slot=1)
        for position, entry in enumerate(view_model.samples):
            row_id = dpg.add_table_row(parent=TAG_SEQUENCER_INSTRUMENTS_TABLE)

            position_cell = dpg.add_table_cell(parent=row_id)
            dpg.add_text(f"{position:02d}", parent=position_cell)

            name_cell = dpg.add_table_cell(parent=row_id)
            name_item = dpg.add_selectable(
                parent=name_cell,
                label=entry.name,
                user_data=entry.sample_id,
                callback=self._on_sample_selected,
            )
            FontRegistry.bind_to_item(name_item, Font.REGULAR_SMALL)
            dpg.bind_item_handler_registry(name_item, self._row_handler_tag)

    def _on_sample_selected(self, sender: Sender, app_data: bool, user_data: str) -> None:
        self.call(self.on_sample_selected, user_data)

    def _on_sample_double_clicked(self, sender: Sender, app_data: list[int]) -> None:
        clicked_item = app_data[1]
        sample_id = dpg.get_item_user_data(clicked_item)
        if isinstance(sample_id, str):
            self.call(self.on_sample_edit_requested, sample_id)
