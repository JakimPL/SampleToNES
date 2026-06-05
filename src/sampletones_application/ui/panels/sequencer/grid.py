from typing import Callable, Dict, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.global_ import StatusElements
from sampletones_application.categories.elements.sequencer import SequencerGridElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.constants.general import (
    SUF_HANDLER_REGISTRY,
    SUF_PANEL_CENTER,
    TAG_GLOBAL_TAB_SEQUENCER,
)
from sampletones_application.constants.sequencer import (
    TAG_SEQUENCER_GRID_BUTTON_EXPORT_MODULE,
    TAG_SEQUENCER_GRID_GROUP_MODULE_OPTIONS,
    TAG_SEQUENCER_GRID_INPUT_NES_FREQUENCY,
    TAG_SEQUENCER_GRID_INPUT_SPEED,
    TAG_SEQUENCER_GRID_INPUT_TEMPO,
    TAG_SEQUENCER_GRID_PANEL,
    TAG_SEQUENCER_GRID_PANEL_PLAYER,
    TAG_SEQUENCER_GRID_TABLE_TRACKER,
    TAG_SEQUENCER_GRID_WINDOW_TRACKER,
)
from sampletones_application.layout.player import PlayerLayout
from sampletones_application.layout.sequencer import SequencerLayout
from sampletones_application.logic.sequencer.grid import SequencerGridLogic
from sampletones_application.logic.shared.player import PlayerLogic
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.panels.player import GUIAudioPlayerPanel
from sampletones_application.ui.themes.tables.pattern import PatternTableTheme
from sampletones_application.utils.dialogs import DialogsRenderer
from sampletones_application.view_model.sequencer.grid import SequencerGridViewModel
from sampletones_application.view_model.sequencer.settings import SequencerSettingsViewModel
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

        self._item_handler_tag = f"{TAG_SEQUENCER_GRID_PANEL}{SUF_HANDLER_REGISTRY}"
        self._rows: Dict[Optional[int], Sender] = {}
        self._highlighted_row: Optional[int] = None

        self.on_change_rate: Optional[Callable[[int], None]] = None
        self.on_tempo: Optional[Callable[[int], None]] = None
        self.on_speed: Optional[Callable[[int], None]] = None

        self.pattern_theme = PatternTableTheme()

        self._lbl_module_options = language_manager[
            Page.SEQUENCER,
            Panel.GRID,
            TextType.LABEL,
            SequencerGridElements.MODULE_OPTIONS,
        ]
        self._lbl_nes_frequency = language_manager[
            Page.SEQUENCER,
            Panel.GRID,
            TextType.LABEL,
            SequencerGridElements.NES_FREQUENCY,
        ]
        self._lbl_tempo = language_manager[
            Page.SEQUENCER,
            Panel.GRID,
            TextType.LABEL,
            SequencerGridElements.TEMPO,
        ]
        self._lbl_speed = language_manager[
            Page.SEQUENCER,
            Panel.GRID,
            TextType.LABEL,
            SequencerGridElements.SPEED,
        ]
        self._lbl_export_module = language_manager[
            Page.SEQUENCER,
            Panel.GRID,
            TextType.LABEL,
            SequencerGridElements.EXPORT_MODULE_BUTTON,
        ]
        self._lbl_tracker = language_manager[
            Page.SEQUENCER,
            Panel.GRID,
            TextType.LABEL,
            SequencerGridElements.TRACKER_TEXT,
        ]
        self._lbl_col_row = language_manager[
            Page.SEQUENCER,
            Panel.GRID,
            TextType.LABEL,
            SequencerGridElements.COLUMN_ROW,
        ]
        self._lbl_col_sample = language_manager[
            Page.SEQUENCER,
            Panel.GRID,
            TextType.LABEL,
            SequencerGridElements.COLUMN_SAMPLE,
        ]
        self._lbl_col_pulse_1 = language_manager[
            Page.SEQUENCER,
            Panel.GRID,
            TextType.LABEL,
            SequencerGridElements.COLUMN_PULSE_1,
        ]
        self._lbl_col_pulse_2 = language_manager[
            Page.SEQUENCER,
            Panel.GRID,
            TextType.LABEL,
            SequencerGridElements.COLUMN_PULSE_2,
        ]
        self._lbl_col_triangle = language_manager[
            Page.SEQUENCER,
            Panel.GRID,
            TextType.LABEL,
            SequencerGridElements.COLUMN_TRIANGLE,
        ]
        self._lbl_col_noise = language_manager[
            Page.SEQUENCER,
            Panel.GRID,
            TextType.LABEL,
            SequencerGridElements.COLUMN_NOISE,
        ]
        self._msg_status_input = language_manager[
            Page.GLOBAL,
            Panel.STATUS,
            TextType.MESSAGE,
            StatusElements.INPUT,
        ]

        super().__init__(
            tag=TAG_SEQUENCER_GRID_PANEL,
            parent=f"{TAG_GLOBAL_TAB_SEQUENCER}{SUF_PANEL_CENTER}",
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
            dpg.add_item_hover_handler(
                parent=self._item_handler_tag,
                callback=self._on_item_hovered,
            )
            dpg.add_item_clicked_handler(
                parent=self._item_handler_tag,
                callback=self._on_item_hovered,
            )

    def _create_audio_panel(self) -> None:
        self.player_panel = GUIAudioPlayerPanel(
            tag=TAG_SEQUENCER_GRID_PANEL_PLAYER,
            parent=TAG_SEQUENCER_GRID_PANEL,
            player_logic=self._player_logic,
            layout=self._layout_player,
            language_manager=self._language_manager,
            dialogs=self._dialogs,
        )

    def _create_module_options(self) -> None:
        dpg.add_separator()
        section_text = dpg.add_text(self._lbl_module_options)
        FontRegistry.bind_to_item(section_text, Font.BOLD)

        settings = self.sequencer_grid_logic.settings
        with dpg.group(tag=TAG_SEQUENCER_GRID_GROUP_MODULE_OPTIONS):
            dpg.add_input_int(
                label=self._lbl_nes_frequency,
                default_value=settings.change_rate,
                tag=TAG_SEQUENCER_GRID_INPUT_NES_FREQUENCY,
                min_value=MIN_CHANGE_RATE,
                max_value=MAX_CHANGE_RATE,
                width=self._input_width,
                callback=self._on_change_rate_input,
            )
            dpg.add_input_int(
                label=self._lbl_tempo,
                default_value=settings.tempo,
                tag=TAG_SEQUENCER_GRID_INPUT_TEMPO,
                min_value=self._layout.tempo.min,
                max_value=self._layout.tempo.max,
                width=self._input_width,
                callback=self._on_tempo_input,
            )
            dpg.add_input_int(
                label=self._lbl_speed,
                default_value=settings.speed,
                tag=TAG_SEQUENCER_GRID_INPUT_SPEED,
                min_value=self._layout.speed.min,
                max_value=self._layout.speed.max,
                width=self._input_width,
                callback=self._on_speed_input,
            )

        GUIStatusBar.bind_to_item(
            TAG_SEQUENCER_GRID_INPUT_NES_FREQUENCY,
            self._msg_status_input,
        )
        GUIStatusBar.bind_to_item(
            TAG_SEQUENCER_GRID_INPUT_TEMPO,
            self._msg_status_input,
        )
        GUIStatusBar.bind_to_item(
            TAG_SEQUENCER_GRID_INPUT_SPEED,
            self._msg_status_input,
        )

    def _create_export_button(self) -> None:
        dpg.add_separator()
        GUIButton(
            tag=TAG_SEQUENCER_GRID_BUTTON_EXPORT_MODULE,
            label=self._lbl_export_module,
            width=-1,
            font=Font.BOLD,
        )

    def _create_tracker_view(self) -> None:
        dpg.add_separator()
        section_text = dpg.add_text(self._lbl_tracker)
        FontRegistry.bind_to_item(section_text, Font.BOLD)

        with dpg.child_window(
            tag=TAG_SEQUENCER_GRID_WINDOW_TRACKER,
            width=0,
            height=-1,
        ):
            with dpg.table(
                tag=TAG_SEQUENCER_GRID_TABLE_TRACKER,
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

        self.pattern_theme.bind_to_item(TAG_SEQUENCER_GRID_TABLE_TRACKER)

    def update_settings(self, view_model: SequencerSettingsViewModel) -> None:
        dpg.set_value(TAG_SEQUENCER_GRID_INPUT_NES_FREQUENCY, view_model.change_rate)
        dpg.set_value(TAG_SEQUENCER_GRID_INPUT_TEMPO, view_model.tempo)
        dpg.set_value(TAG_SEQUENCER_GRID_INPUT_SPEED, view_model.speed)

    def update_grid(self, view_model: SequencerGridViewModel) -> None:
        """Rebuilds the tracker body from scratch for the visible order frame.

        Patterns vary in length, so rows are recreated rather than mutated in
        place; the table columns (slot 0) are kept and only the row slot is
        cleared.
        """
        dpg.delete_item(
            TAG_SEQUENCER_GRID_TABLE_TRACKER,
            children_only=True,
            slot=1,
        )
        self._rows = {}

        for row in view_model.rows:
            with dpg.table_row(
                parent=TAG_SEQUENCER_GRID_TABLE_TRACKER,
                user_data=row.index,
            ):
                with dpg.table_cell():
                    dpg.add_spacer(width=0)
                with dpg.table_cell():
                    selectable = dpg.add_selectable(
                        label=f"{row.index:02d}",
                        span_columns=True,
                        user_data=row.index,
                    )
                    FontRegistry.bind_to_item(selectable, Font.REGULAR_SMALL)
                    dpg.bind_item_handler_registry(
                        selectable,
                        self._item_handler_tag,
                    )
                    self._rows[row.index] = selectable
                with dpg.table_cell():
                    sample_text = dpg.add_selectable(label="")
                    FontRegistry.bind_to_item(sample_text, Font.BOLD_SMALL)
                for generator in GeneratorName.items():
                    with dpg.table_cell():
                        cell_text = dpg.add_selectable(
                            label=row.cells[generator].label,
                        )
                        FontRegistry.bind_to_item(cell_text, Font.REGULAR_SMALL)

    def _on_change_rate_input(self, sender: Sender, app_data: int) -> None:
        self.call(self.on_change_rate, app_data)

    def _on_tempo_input(self, sender: Sender, app_data: int) -> None:
        self.call(self.on_tempo, app_data)

    def _on_speed_input(self, sender: Sender, app_data: int) -> None:
        self.call(self.on_speed, app_data)

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
            TAG_SEQUENCER_GRID_TABLE_TRACKER,
            row_index,
            color=self._layout.colors.pattern_highlight,
        )

    def unhighlight_row(self, row_index: Optional[int] = None) -> None:
        if row_index is None:
            return

        dpg.unhighlight_table_row(
            TAG_SEQUENCER_GRID_TABLE_TRACKER,
            row_index,
        )
        self._highlighted_row = None
