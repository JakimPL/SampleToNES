from typing import Dict, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.constants.general import (
    MSG_STATUS_INPUT,
    SUF_HANDLER_REGISTRY,
    SUF_PANEL_CENTER,
    TAG_TAB_GLOBAL_SEQUENCER,
)
from sampletones_application.constants.sequencer import (
    TAG_BUTTON_SEQUENCER_GRID_EXPORT_MODULE,
    TAG_GROUP_SEQUENCER_GRID_MODULE_OPTIONS,
    TAG_INPUT_SEQUENCER_GRID_NES_FREQUENCY,
    TAG_INPUT_SEQUENCER_GRID_SPEED,
    TAG_INPUT_SEQUENCER_GRID_TEMPO,
    TAG_PANEL_SEQUENCER_GRID,
    TAG_PANEL_SEQUENCER_GRID_PLAYER,
    TAG_TABLE_SEQUENCER_GRID_TRACKER,
    TAG_WINDOW_SEQUENCER_GRID_TRACKER,
)
from sampletones_application.layout.player import PlayerLayout
from sampletones_application.layout.sequencer import SequencerLayout
from sampletones_application.logic.sequencer.grid import SequencerGridLogic
from sampletones_application.logic.shared.player import PlayerLogic
from sampletones_application.text.elements.sequencer import SequencerGridElements
from sampletones_application.text.hierarchy import Page, Panel, TextType
from sampletones_application.text.key import TextKey
from sampletones_application.text.manager import LanguageManager
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.panels.player import GUIAudioPlayerPanel
from sampletones_application.ui.themes.tables.pattern import PatternTableTheme
from sampletones_application.utils.dialogs import DialogsRenderer
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.constants.general import MAX_CHANGE_RATE, MIN_CHANGE_RATE
from sampletones_shared.types.application import Sender


class GUISequencerGridPanel(GUIPanel):
    def __init__(
        self,
        sequencer_grid_logic: SequencerGridLogic,
        player_logic: PlayerLogic,
        *,
        layout: SequencerLayout,
        layout_player: PlayerLayout,
        input_width: int,
        language_manager: LanguageManager,
        dialogs: DialogsRenderer,
    ) -> None:
        self.sequencer_grid_logic = sequencer_grid_logic
        self._player_logic = player_logic
        self._layout = layout
        self._layout_player = layout_player
        self._input_width = input_width
        self._language_manager = language_manager
        self._dialogs = dialogs

        self.player_panel: GUIAudioPlayerPanel

        self._item_handler_tag = f"{TAG_PANEL_SEQUENCER_GRID}{SUF_HANDLER_REGISTRY}"
        self._rows: Dict[Optional[int], Sender] = {}
        self._highlighted_row: Optional[int] = None

        self.pattern_theme = PatternTableTheme()

        self._lbl_module_options = language_manager[
            TextKey(Page.SEQUENCER, Panel.GRID, TextType.LABEL, SequencerGridElements.MODULE_OPTIONS)
        ]
        self._lbl_nes_frequency = language_manager[
            TextKey(Page.SEQUENCER, Panel.GRID, TextType.LABEL, SequencerGridElements.NES_FREQUENCY)
        ]
        self._lbl_tempo = language_manager[
            TextKey(Page.SEQUENCER, Panel.GRID, TextType.LABEL, SequencerGridElements.TEMPO)
        ]
        self._lbl_speed = language_manager[
            TextKey(Page.SEQUENCER, Panel.GRID, TextType.LABEL, SequencerGridElements.SPEED)
        ]
        self._lbl_export_module = language_manager[
            TextKey(Page.SEQUENCER, Panel.GRID, TextType.LABEL, SequencerGridElements.EXPORT_MODULE_BUTTON)
        ]
        self._lbl_tracker = language_manager[
            TextKey(Page.SEQUENCER, Panel.GRID, TextType.LABEL, SequencerGridElements.TRACKER_TEXT)
        ]
        self._lbl_col_row = language_manager[
            TextKey(Page.SEQUENCER, Panel.GRID, TextType.LABEL, SequencerGridElements.COLUMN_ROW)
        ]
        self._lbl_col_sample = language_manager[
            TextKey(Page.SEQUENCER, Panel.GRID, TextType.LABEL, SequencerGridElements.COLUMN_SAMPLE)
        ]
        self._lbl_col_pulse_1 = language_manager[
            TextKey(Page.SEQUENCER, Panel.GRID, TextType.LABEL, SequencerGridElements.COLUMN_PULSE_1)
        ]
        self._lbl_col_pulse_2 = language_manager[
            TextKey(Page.SEQUENCER, Panel.GRID, TextType.LABEL, SequencerGridElements.COLUMN_PULSE_2)
        ]
        self._lbl_col_triangle = language_manager[
            TextKey(Page.SEQUENCER, Panel.GRID, TextType.LABEL, SequencerGridElements.COLUMN_TRIANGLE)
        ]
        self._lbl_col_noise = language_manager[
            TextKey(Page.SEQUENCER, Panel.GRID, TextType.LABEL, SequencerGridElements.COLUMN_NOISE)
        ]

        super().__init__(
            tag=TAG_PANEL_SEQUENCER_GRID,
            parent=f"{TAG_TAB_GLOBAL_SEQUENCER}{SUF_PANEL_CENTER}",
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
            player_logic=self._player_logic,
            layout=self._layout_player,
            language_manager=self._language_manager,
            dialogs=self._dialogs,
        )

    def _create_module_options(self) -> None:
        dpg.add_separator()
        section_text = dpg.add_text(self._lbl_module_options)
        FontRegistry.bind_to_item(section_text, Font.BOLD)

        with dpg.group(tag=TAG_GROUP_SEQUENCER_GRID_MODULE_OPTIONS):
            dpg.add_input_int(
                label=self._lbl_nes_frequency,
                default_value=self.sequencer_grid_logic.change_rate,
                tag=TAG_INPUT_SEQUENCER_GRID_NES_FREQUENCY,
                min_value=MIN_CHANGE_RATE,
                max_value=MAX_CHANGE_RATE,
                width=self._input_width,
            )
            dpg.add_input_int(
                label=self._lbl_tempo,
                default_value=self._layout.tempo.default,
                tag=TAG_INPUT_SEQUENCER_GRID_TEMPO,
                min_value=self._layout.tempo.min,
                max_value=self._layout.tempo.max,
                width=self._input_width,
            )
            dpg.add_input_int(
                label=self._lbl_speed,
                default_value=self._layout.speed.default,
                tag=TAG_INPUT_SEQUENCER_GRID_SPEED,
                min_value=self._layout.speed.min,
                max_value=self._layout.speed.max,
                width=self._input_width,
            )

        GUIStatusBar.bind_to_item(TAG_INPUT_SEQUENCER_GRID_NES_FREQUENCY, MSG_STATUS_INPUT)
        GUIStatusBar.bind_to_item(TAG_INPUT_SEQUENCER_GRID_TEMPO, MSG_STATUS_INPUT)
        GUIStatusBar.bind_to_item(TAG_INPUT_SEQUENCER_GRID_SPEED, MSG_STATUS_INPUT)

    def _create_export_button(self) -> None:
        dpg.add_separator()
        GUIButton(
            tag=TAG_BUTTON_SEQUENCER_GRID_EXPORT_MODULE,
            label=self._lbl_export_module,
            width=-1,
            font=Font.BOLD,
        )

    def _create_tracker_view(self) -> None:
        dpg.add_separator()
        section_text = dpg.add_text(self._lbl_tracker)
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
                    label=self._lbl_col_row,
                    width_fixed=True,
                    init_width_or_weight=self._layout.table_cells.row,
                )
                dpg.add_table_column(
                    label=self._lbl_col_sample,
                    width_fixed=True,
                    init_width_or_weight=self._layout.table_cells.sample,
                )
                dpg.add_table_column(
                    label=self._lbl_col_pulse_1,
                    width_fixed=True,
                    init_width_or_weight=self._layout.table_cells.generator,
                )
                dpg.add_table_column(
                    label=self._lbl_col_pulse_2,
                    width_fixed=True,
                    init_width_or_weight=self._layout.table_cells.generator,
                )
                dpg.add_table_column(
                    label=self._lbl_col_triangle,
                    width_fixed=True,
                    init_width_or_weight=self._layout.table_cells.generator,
                )
                dpg.add_table_column(
                    label=self._lbl_col_noise,
                    width_fixed=True,
                    init_width_or_weight=self._layout.table_cells.generator,
                )
                dpg.add_table_column(width_stretch=True)

                for row_index in range(self._layout.tracker.rows):
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
            color=self._layout.colors.pattern_highlight,
        )

    def unhighlight_row(self, row_index: Optional[int] = None) -> None:
        if row_index is None:
            return

        dpg.unhighlight_table_row(
            TAG_TABLE_SEQUENCER_GRID_TRACKER,
            row_index,
        )
        self._highlighted_row = None
