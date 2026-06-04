import dearpygui.dearpygui as dpg

from sampletones_application.constants.general import (
    TAG_THEME_GLOBAL_FILE_LIBRARY,
    TAG_THEME_GLOBAL_FILE_NO_CONTENT,
    TAG_THEME_GLOBAL_FILE_NOT_EXPANDED_DIRECTORY,
    TAG_THEME_GLOBAL_FILE_RECONSTRUCTION,
    TAG_THEME_GLOBAL_FILE_WAVE,
)
from sampletones_application.layout.general import GeneralLayout
from sampletones_application.ui.themes.items import ThemeItems
from sampletones_application.ui.themes.style import ThemeColor, ThemeParameter
from sampletones_application.ui.themes.theme import Theme


class NoContentFileNodeTheme(Theme):
    tag: str = TAG_THEME_GLOBAL_FILE_NO_CONTENT
    _theme: ThemeItems = ThemeItems()

    @classmethod
    def setup(cls, layout: GeneralLayout) -> None:
        cls._theme = ThemeItems(
            items={
                ThemeParameter(item_type=dpg.mvTreeNode): [
                    ThemeColor(
                        key=dpg.mvThemeCol_Text,
                        color=layout.colors.text.disabled,
                    ),
                ],
            }
        )


class ReconstructionFileNodeTheme(Theme):
    tag: str = TAG_THEME_GLOBAL_FILE_RECONSTRUCTION
    _theme: ThemeItems = ThemeItems()

    @classmethod
    def setup(cls, layout: GeneralLayout) -> None:
        cls._theme = ThemeItems(
            items={
                ThemeParameter(item_type=dpg.mvTreeNode): [
                    ThemeColor(
                        key=dpg.mvThemeCol_Text,
                        color=layout.colors.files.reconstruction,
                    ),
                ],
            }
        )


class LibraryFileNodeTheme(Theme):
    tag: str = TAG_THEME_GLOBAL_FILE_LIBRARY
    _theme: ThemeItems = ThemeItems()

    @classmethod
    def setup(cls, layout: GeneralLayout) -> None:
        cls._theme = ThemeItems(
            items={
                ThemeParameter(item_type=dpg.mvTreeNode): [
                    ThemeColor(
                        key=dpg.mvThemeCol_Text,
                        color=layout.colors.files.library,
                    ),
                ],
            }
        )


class WaveFileNodeTheme(Theme):
    tag: str = TAG_THEME_GLOBAL_FILE_WAVE
    _theme: ThemeItems = ThemeItems()

    @classmethod
    def setup(cls, layout: GeneralLayout) -> None:
        cls._theme = ThemeItems(
            items={
                ThemeParameter(item_type=dpg.mvTreeNode): [
                    ThemeColor(
                        key=dpg.mvThemeCol_Text,
                        color=layout.colors.files.wave,
                    ),
                ],
            }
        )


class NotExpandedDirectoryNodeTheme(Theme):
    tag: str = TAG_THEME_GLOBAL_FILE_NOT_EXPANDED_DIRECTORY
    _theme: ThemeItems = ThemeItems()

    @classmethod
    def setup(cls, layout: GeneralLayout) -> None:
        cls._theme = ThemeItems(
            items={
                ThemeParameter(item_type=dpg.mvTreeNode): [
                    ThemeColor(
                        key=dpg.mvThemeCol_Text,
                        color=layout.colors.files.directory_not_expanded,
                    ),
                ],
            }
        )
