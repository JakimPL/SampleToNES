import dearpygui.dearpygui as dpg

from sampletones_application.constants.reconstructions import TAG_THEME_TABLE_RECONSTRUCTIONS_DETAILS_INITIAL_PITCH
from sampletones_application.layout.reconstructions import ReconstructionsLayout
from sampletones_application.ui.themes.items import ThemeItems
from sampletones_application.ui.themes.style import ThemeParameter, ThemeStyle
from sampletones_application.ui.themes.theme import Theme


class InitialPitchTableTheme(Theme):
    tag: str = TAG_THEME_TABLE_RECONSTRUCTIONS_DETAILS_INITIAL_PITCH
    _theme: ThemeItems = ThemeItems()

    @classmethod
    def setup(cls, layout: ReconstructionsLayout) -> None:
        cp = layout.initial_pitch_table.cell_padding
        cls._theme = ThemeItems(
            items={
                ThemeParameter(item_type=dpg.mvTable): [
                    ThemeStyle(
                        key=dpg.mvStyleVar_CellPadding,
                        x=cp[0],
                        y=cp[1],
                    ),
                ],
            }
        )
