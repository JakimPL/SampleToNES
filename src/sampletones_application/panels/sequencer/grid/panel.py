from typing import Dict, Optional

import dearpygui.dearpygui as dpg

from sampletones_core.audio import AudioDeviceManager
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.constants.general import MAX_CHANGE_RATE, MIN_CHANGE_RATE
from sampletones_shared.types.application import Sender

from ....constants.general import (
    DIM_INPUT_WIDTH,
    MSG_STATUS_INPUT,
    SUF_HANDLER_REGISTRY,
    SUF_PANEL_CENTER,
    TAG_TAB_SEQUENCER,
)
from ....constants.sequencer import (
    COL_PATTERN_HIGHLIGHT,
    DIM_TABLE_CELL_WIDTH_SEQUENCER_GRID_GENERATOR,
    DIM_TABLE_CELL_WIDTH_SEQUENCER_GRID_ROW,
    DIM_TABLE_CELL_WIDTH_SEQUENCER_GRID_SAMPLE,
    LBL_BUTTON_SEQUENCER_GRID_EXPORT_MODULE,
    LBL_TABLE_SEQUENCER_GRID_COLUMN_NOISE,
    LBL_TABLE_SEQUENCER_GRID_COLUMN_PULSE_1,
    LBL_TABLE_SEQUENCER_GRID_COLUMN_PULSE_2,
    LBL_TABLE_SEQUENCER_GRID_COLUMN_ROW,
    LBL_TABLE_SEQUENCER_GRID_COLUMN_SAMPLE,
    LBL_TABLE_SEQUENCER_GRID_COLUMN_TRIANGLE,
    LBL_TEXT_SEQUENCER_GRID_MODULE_OPTIONS,
    LBL_TEXT_SEQUENCER_GRID_NES_FREQUENCY,
    LBL_TEXT_SEQUENCER_GRID_SPEED,
    LBL_TEXT_SEQUENCER_GRID_TEMPO,
    LBL_TEXT_SEQUENCER_GRID_TRACKER,
    TAG_BUTTON_SEQUENCER_GRID_EXPORT_MODULE,
    TAG_GROUP_SEQUENCER_GRID_MODULE_OPTIONS,
    TAG_INPUT_SEQUENCER_GRID_NES_FREQUENCY,
    TAG_INPUT_SEQUENCER_GRID_SPEED,
    TAG_INPUT_SEQUENCER_GRID_TEMPO,
    TAG_PANEL_SEQUENCER_GRID,
    TAG_PANEL_SEQUENCER_GRID_PLAYER,
    TAG_TABLE_SEQUENCER_GRID_TRACKER,
    TAG_WINDOW_SEQUENCER_GRID_TRACKER,
    VAL_SEQUENCER_GRID_SPEED_DEFAULT,
    VAL_SEQUENCER_GRID_SPEED_MAX,
    VAL_SEQUENCER_GRID_SPEED_MIN,
    VAL_SEQUENCER_GRID_TEMPO_DEFAULT,
    VAL_SEQUENCER_GRID_TEMPO_MAX,
    VAL_SEQUENCER_GRID_TEMPO_MIN,
    VAL_SEQUENCER_GRID_TRACKER_ROWS,
)
from ....elements.button import GUIButton
from ....elements.fonts.font import Font
from ....elements.fonts.registry import FontRegistry
from ....elements.panel import GUIPanel
from ....elements.status import GUIStatusBar
from ....panels.player import GUIAudioPlayerPanel
from ....themes.tables.pattern import PatternTableTheme
from .logic import SequencerGridLogic


class GUISequencerGridPanel(GUIPanel):
    def __init__(
        self,
        sequencer_grid_logic: SequencerGridLogic,
        audio_device_manager: AudioDeviceManager,
    ) -> None:
        self.sequencer_grid_logic = sequencer_grid_logic
        self.audio_device_manager = audio_device_manager

        self.player_panel: GUIAudioPlayerPanel

        self._item_handler_tag = f"{TAG_PANEL_SEQUENCER_GRID}{SUF_HANDLER_REGISTRY}"
        self._rows: Dict[Optional[int], Sender] = {}
        self._highlighted_row: Optional[int] = None

        self.pattern_theme = PatternTableTheme()

        super().__init__(
            tag=TAG_PANEL_SEQUENCER_GRID,
            parent=f"{TAG_TAB_SEQUENCER}{SUF_PANEL_CENTER}",
        )

    def create_panel(self) -> None:
        self._setup_handlers()
        with dpg.child_window(
            tag=self.tag,
            width=self.width,
            height=self.height,
            parent=self.parent,
            border=False,
        ):
            self._create_audio_panel()
            self._create_module_options()
            self._create_export_button()
            self._create_tracker_view()

    def _setup_handlers(self) -> None:
        with dpg.item_handler_registry(tag=self._item_handler_tag):
            dpg.add_item_hover_handler(parent=self._item_handler_tag, callback=self._on_item_hovered)
            dpg.add_item_clicked_handler(parent=self._item_handler_tag, callback=self._on_item_hovered)

    def _create_audio_panel(self) -> None:
        self.player_panel = GUIAudioPlayerPanel(
            tag=TAG_PANEL_SEQUENCER_GRID_PLAYER,
            parent=TAG_PANEL_SEQUENCER_GRID,
            audio_device_manager=self.audio_device_manager,
        )

    def _create_module_options(self) -> None:
        dpg.add_separator()
        section_text = dpg.add_text(LBL_TEXT_SEQUENCER_GRID_MODULE_OPTIONS)
        FontRegistry.bind_to_item(section_text, Font.BOLD)

        with dpg.group(tag=TAG_GROUP_SEQUENCER_GRID_MODULE_OPTIONS):
            dpg.add_input_int(
                label=LBL_TEXT_SEQUENCER_GRID_NES_FREQUENCY,
                default_value=self.sequencer_grid_logic.change_rate,
                tag=TAG_INPUT_SEQUENCER_GRID_NES_FREQUENCY,
                min_value=MIN_CHANGE_RATE,
                max_value=MAX_CHANGE_RATE,
                width=DIM_INPUT_WIDTH,
            )
            dpg.add_input_int(
                label=LBL_TEXT_SEQUENCER_GRID_TEMPO,
                default_value=VAL_SEQUENCER_GRID_TEMPO_DEFAULT,
                tag=TAG_INPUT_SEQUENCER_GRID_TEMPO,
                min_value=VAL_SEQUENCER_GRID_TEMPO_MIN,
                max_value=VAL_SEQUENCER_GRID_TEMPO_MAX,
                width=DIM_INPUT_WIDTH,
            )
            dpg.add_input_int(
                label=LBL_TEXT_SEQUENCER_GRID_SPEED,
                default_value=VAL_SEQUENCER_GRID_SPEED_DEFAULT,
                tag=TAG_INPUT_SEQUENCER_GRID_SPEED,
                min_value=VAL_SEQUENCER_GRID_SPEED_MIN,
                max_value=VAL_SEQUENCER_GRID_SPEED_MAX,
                width=DIM_INPUT_WIDTH,
            )

        GUIStatusBar.bind_to_item(TAG_INPUT_SEQUENCER_GRID_NES_FREQUENCY, MSG_STATUS_INPUT)
        GUIStatusBar.bind_to_item(TAG_INPUT_SEQUENCER_GRID_TEMPO, MSG_STATUS_INPUT)
        GUIStatusBar.bind_to_item(TAG_INPUT_SEQUENCER_GRID_SPEED, MSG_STATUS_INPUT)

    def _create_export_button(self) -> None:
        dpg.add_separator()
        GUIButton(
            tag=TAG_BUTTON_SEQUENCER_GRID_EXPORT_MODULE,
            label=LBL_BUTTON_SEQUENCER_GRID_EXPORT_MODULE,
            width=-1,
            font=Font.BOLD,
        )

    def _create_tracker_view(self) -> None:
        dpg.add_separator()
        section_text = dpg.add_text(LBL_TEXT_SEQUENCER_GRID_TRACKER)
        FontRegistry.bind_to_item(section_text, Font.BOLD)

        with dpg.child_window(
            tag=TAG_WINDOW_SEQUENCER_GRID_TRACKER,
            width=0,
            height=-1,
        ):
            with dpg.table(
                tag=TAG_TABLE_SEQUENCER_GRID_TRACKER,
                width=0,
                header_row=True,
                resizable=False,
                borders_innerH=False,
                borders_innerV=True,
                borders_outerH=True,
                borders_outerV=True,
                scrollX=True,
                scrollY=True,
                row_background=True,
                policy=dpg.mvTable_SizingFixedFit,
            ):
                FontRegistry.bind_to_item(dpg.last_item(), Font.BOLD)
                dpg.add_table_column(width_stretch=True)
                dpg.add_table_column(
                    label=LBL_TABLE_SEQUENCER_GRID_COLUMN_ROW,
                    width_fixed=True,
                    init_width_or_weight=DIM_TABLE_CELL_WIDTH_SEQUENCER_GRID_ROW,
                )
                dpg.add_table_column(
                    label=LBL_TABLE_SEQUENCER_GRID_COLUMN_SAMPLE,
                    width_fixed=True,
                    init_width_or_weight=DIM_TABLE_CELL_WIDTH_SEQUENCER_GRID_SAMPLE,
                )
                dpg.add_table_column(
                    label=LBL_TABLE_SEQUENCER_GRID_COLUMN_PULSE_1,
                    width_fixed=True,
                    init_width_or_weight=DIM_TABLE_CELL_WIDTH_SEQUENCER_GRID_GENERATOR,
                )
                dpg.add_table_column(
                    label=LBL_TABLE_SEQUENCER_GRID_COLUMN_PULSE_2,
                    width_fixed=True,
                    init_width_or_weight=DIM_TABLE_CELL_WIDTH_SEQUENCER_GRID_GENERATOR,
                )
                dpg.add_table_column(
                    label=LBL_TABLE_SEQUENCER_GRID_COLUMN_TRIANGLE,
                    width_fixed=True,
                    init_width_or_weight=DIM_TABLE_CELL_WIDTH_SEQUENCER_GRID_GENERATOR,
                )
                dpg.add_table_column(
                    label=LBL_TABLE_SEQUENCER_GRID_COLUMN_NOISE,
                    width_fixed=True,
                    init_width_or_weight=DIM_TABLE_CELL_WIDTH_SEQUENCER_GRID_GENERATOR,
                )
                dpg.add_table_column(width_stretch=True)

                for row_index in range(VAL_SEQUENCER_GRID_TRACKER_ROWS):
                    with dpg.table_row(user_data=row_index):
                        with dpg.table_cell():
                            dpg.add_spacer(width=0)
                        with dpg.table_cell():
                            selectable = dpg.add_selectable(
                                label=f"{row_index:02d}",
                                span_columns=True,
                                user_data=row_index,
                            )
                            FontRegistry.bind_to_item(selectable, Font.REGULAR_SMALL)
                            dpg.bind_item_handler_registry(selectable, self._item_handler_tag)
                            self._rows[row_index] = selectable
                        with dpg.table_cell():
                            instrument_text = dpg.add_selectable(label=".. . ...")
                            FontRegistry.bind_to_item(instrument_text, Font.BOLD_SMALL)
                        for _ in range(len(GeneratorName)):
                            with dpg.table_cell():
                                generator_text = dpg.add_selectable(label="... .")
                                FontRegistry.bind_to_item(generator_text, Font.REGULAR_SMALL)

        self.pattern_theme.bind_to_item(TAG_TABLE_SEQUENCER_GRID_TRACKER)

    def _on_item_hovered(self, sender: Sender, app_data: int) -> None:
        if not dpg.does_item_exist(app_data):
            return

        row_index = dpg.get_item_user_data(app_data)
        if row_index is not None:
            dpg.set_value(app_data, False)
            highlighted_item = self._rows.get(self._highlighted_row)
            if highlighted_item is not None:
                dpg.set_value(highlighted_item, False)
            self._highlighted_row = row_index

    def highlight_row(self, row_index: Optional[int] = None) -> None:
        self.unhighlight_row(self._highlighted_row)
        self._highlighted_row = row_index
        if row_index is None:
            return

        dpg.highlight_table_row(
            TAG_TABLE_SEQUENCER_GRID_TRACKER,
            row_index,
            color=COL_PATTERN_HIGHLIGHT,
        )

    def unhighlight_row(self, row_index: Optional[int] = None) -> None:
        if row_index is None:
            return

        dpg.unhighlight_table_row(
            TAG_TABLE_SEQUENCER_GRID_TRACKER,
            row_index,
        )
        self._highlighted_row = None
