from typing import Callable, Optional, Tuple

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
    TAG_SEQUENCER_INSTRUMENTS_THEME_ROW,
    TAG_SEQUENCER_INSTRUMENTS_WINDOW,
)
from sampletones_application.layout.sequencer import SequencerLayout
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.dpg import dpg_delete_children
from sampletones_application.view_model.sequencer.samples import SampleEntryViewModel, SequencerSamplesViewModel
from sampletones_core.utils.display import display_index
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
        self._selected_sample_id: Optional[str] = None
        self._selected_row: Optional[int] = None
        self.on_sample_selected: Optional[Callable[[str], None]] = None
        self.on_sample_edit_requested: Optional[Callable[[str], None]] = None
        self.on_loop_changed: Optional[Callable[[str, bool], None]] = None
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
        self._lbl_column_loop = language_manager[
            Page.SEQUENCER,
            Panel.INSTRUMENTS,
            TextType.LABEL,
            SequencerInstrumentsElements.COLUMN_LOOP,
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
                dpg.add_table_column(
                    label=self._lbl_column_loop,
                    width_fixed=True,
                    init_width_or_weight=self._layout.table_cells.instrument_loop,
                )
        ThemeRegistry.get(TAG_SEQUENCER_INSTRUMENTS_THEME_ROW).bind_to_item(TAG_SEQUENCER_INSTRUMENTS_TABLE)

    def update_view(self, view_model: SequencerSamplesViewModel) -> None:
        """Rebuilds the samples table with explicit parents.

        Items pass an explicit ``parent`` rather than nesting ``with`` blocks: the
        browser tree builds on a worker thread and the DearPyGui container stack
        is process-global, so ``with`` blocks here would race with it.
        """
        dpg_delete_children(TAG_SEQUENCER_INSTRUMENTS_TABLE, slot=1)
        self._selected_row = None
        for position, entry in enumerate(view_model.samples):
            self._build_sample_row(position, entry)

    def _build_sample_row(self, position: int, entry: SampleEntryViewModel) -> None:
        row_id = dpg.add_table_row(parent=TAG_SEQUENCER_INSTRUMENTS_TABLE)
        self._build_id_cell(row_id, position, entry)
        self._build_name_cell(row_id, position, entry)
        self._build_loop_cell(row_id, entry)
        if entry.sample_id == self._selected_sample_id:
            self._selected_row = position
            dpg.highlight_table_row(TAG_SEQUENCER_INSTRUMENTS_TABLE, position, color=self._layout.colors.cell_cursor)

    def _build_id_cell(self, row_id: int | str, position: int, entry: SampleEntryViewModel) -> None:
        id_cell = dpg.add_table_cell(parent=row_id)
        id_selectable = dpg.add_selectable(
            parent=id_cell,
            label=display_index(position),
            span_columns=True,
            user_data=(position, entry.sample_id),
            callback=self._on_sample_selected,
        )
        FontRegistry.bind_to_item(id_selectable, Font.REGULAR_SMALL)
        dpg.bind_item_handler_registry(id_selectable, self._row_handler_tag)

    def _build_name_cell(self, row_id: int | str, position: int, entry: SampleEntryViewModel) -> None:
        name_cell = dpg.add_table_cell(parent=row_id)
        name_selectable = dpg.add_selectable(
            parent=name_cell,
            label=entry.name,
            user_data=(position, entry.sample_id),
            callback=self._on_sample_selected,
        )
        FontRegistry.bind_to_item(name_selectable, Font.REGULAR_SMALL)
        dpg.bind_item_handler_registry(name_selectable, self._row_handler_tag)

    def _build_loop_cell(self, row_id: int | str, entry: SampleEntryViewModel) -> None:
        loop_cell = dpg.add_table_cell(parent=row_id)
        dpg.add_checkbox(
            parent=loop_cell,
            default_value=entry.loop,
            user_data=entry.sample_id,
            callback=self._on_loop_toggled,
        )

    def _on_sample_selected(self, sender: Sender, app_data: bool, user_data: Tuple[int, str]) -> None:
        position, sample_id = user_data
        dpg.set_value(sender, False)
        if self._selected_row is not None:
            dpg.unhighlight_table_row(TAG_SEQUENCER_INSTRUMENTS_TABLE, self._selected_row)

        self._selected_row = position
        self._selected_sample_id = sample_id
        dpg.highlight_table_row(TAG_SEQUENCER_INSTRUMENTS_TABLE, position, color=self._layout.colors.cell_cursor)
        self.call(self.on_sample_selected, sample_id)

    def _on_loop_toggled(self, sender: Sender, app_data: bool, user_data: str) -> None:
        self.call(self.on_loop_changed, user_data, app_data)

    def _on_sample_double_clicked(self, sender: Sender, app_data: list[int]) -> None:
        clicked_item = app_data[1]
        user_data = dpg.get_item_user_data(clicked_item)
        if user_data is not None:
            _, sample_id = user_data
            self.call(self.on_sample_edit_requested, sample_id)
