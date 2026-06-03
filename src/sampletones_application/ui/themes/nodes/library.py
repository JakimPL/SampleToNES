import dearpygui.dearpygui as dpg

from sampletones_application.constants.instructions import (
    TAG_THEME_INSTRUCTIONS_LIBRARY_GENERATOR,
    TAG_THEME_INSTRUCTIONS_LIBRARY_GROUP,
    TAG_THEME_INSTRUCTIONS_LIBRARY_INSTRUCTION,
    TAG_THEME_INSTRUCTIONS_LIBRARY_LIBRARY,
)
from sampletones_application.layout.instructions import InstructionsLayout
from sampletones_application.ui.themes.items import ThemeItems
from sampletones_application.ui.themes.style import ThemeColor, ThemeParameter
from sampletones_application.ui.themes.theme import Theme


class LibraryLibraryNodeTheme(Theme):
    tag: str = TAG_THEME_INSTRUCTIONS_LIBRARY_LIBRARY
    _theme: ThemeItems = ThemeItems()

    @classmethod
    def setup(cls, layout: InstructionsLayout) -> None:
        cls._theme = ThemeItems(
            items={
                ThemeParameter(item_type=dpg.mvTreeNode): [
                    ThemeColor(key=dpg.mvThemeCol_Text, color=layout.colors.library),
                ],
            }
        )


class LibraryGeneratorNodeTheme(Theme):
    tag: str = TAG_THEME_INSTRUCTIONS_LIBRARY_GENERATOR
    _theme: ThemeItems = ThemeItems()

    @classmethod
    def setup(cls, layout: InstructionsLayout) -> None:
        cls._theme = ThemeItems(
            items={
                ThemeParameter(item_type=dpg.mvTreeNode): [
                    ThemeColor(key=dpg.mvThemeCol_Text, color=layout.colors.generator),
                ],
            }
        )


class LibraryGroupNodeTheme(Theme):
    tag: str = TAG_THEME_INSTRUCTIONS_LIBRARY_GROUP
    _theme: ThemeItems = ThemeItems()

    @classmethod
    def setup(cls, layout: InstructionsLayout) -> None:
        cls._theme = ThemeItems(
            items={
                ThemeParameter(item_type=dpg.mvTreeNode): [
                    ThemeColor(key=dpg.mvThemeCol_Text, color=layout.colors.group),
                ],
            }
        )


class LibraryInstructionNodeTheme(Theme):
    tag: str = TAG_THEME_INSTRUCTIONS_LIBRARY_INSTRUCTION
    _theme: ThemeItems = ThemeItems()

    @classmethod
    def setup(cls, layout: InstructionsLayout) -> None:
        cls._theme = ThemeItems(
            items={
                ThemeParameter(item_type=dpg.mvSelectable): [
                    ThemeColor(key=dpg.mvThemeCol_Text, color=layout.colors.instruction),
                ],
            }
        )
