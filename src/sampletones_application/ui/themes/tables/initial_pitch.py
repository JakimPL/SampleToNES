import dearpygui.dearpygui as dpg

from sampletones_application.constants.reconstructions import TAG_RECONSTRUCTIONS_DETAILS_THEME_INITIAL_PITCH_TABLE
from sampletones_application.layout.reconstructions import ReconstructionsLayout
from sampletones_application.ui.themes.items import ThemeItems
from sampletones_application.ui.themes.style import ThemeParameter, ThemeStyle
from sampletones_application.ui.themes.theme import Theme


class InitialPitchTableTheme(Theme):
    tag: str = TAG_RECONSTRUCTIONS_DETAILS_THEME_INITIAL_PITCH_TABLE
    _theme: ThemeItems = ThemeItems()

    @classmethod
    def setup(cls, layout: ReconstructionsLayout) -> None:
        cell_padding = layout.initial_pitch_table.cell_padding
        cls._theme = ThemeItems(
            items={
                ThemeParameter(item_type=dpg.mvTable): [
                    ThemeStyle(
                        key=dpg.mvStyleVar_CellPadding,
                        x=cell_padding[0],
                        y=cell_padding[1],
                    ),
                ],
            }
        )
