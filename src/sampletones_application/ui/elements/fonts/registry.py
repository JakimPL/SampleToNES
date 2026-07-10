from typing import Dict, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.layout.general import FontsLayout
from sampletones_application.tags.general import (
    TAG_GLOBAL_FONT_BOLD,
    TAG_GLOBAL_FONT_BOLD_LARGE,
    TAG_GLOBAL_FONT_BOLD_SMALL,
    TAG_GLOBAL_FONT_ICON,
    TAG_GLOBAL_FONT_ITALIC,
    TAG_GLOBAL_FONT_ITALIC_LARGE,
    TAG_GLOBAL_FONT_ITALIC_SMALL,
    TAG_GLOBAL_FONT_REGULAR,
    TAG_GLOBAL_FONT_REGULAR_LARGE,
    TAG_GLOBAL_FONT_REGULAR_SMALL,
)
from sampletones_application.ui.elements.fonts.data import FontData
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.resources.items import FontResource
from sampletones_application.ui.resources.resources import get_font_path
from sampletones_shared.types.application import Sender


class FontRegistry:
    _LAYOUT: FontsLayout
    _REGISTRY: Dict[Font, FontData] = {}

    @classmethod
    def setup(cls, layout: FontsLayout) -> None:
        cls._LAYOUT = layout
        cls._REGISTRY = {
            Font.REGULAR: FontData(
                TAG_GLOBAL_FONT_REGULAR,
                layout.size,
                FontResource.REGULAR,
            ),
            Font.REGULAR_SMALL: FontData(
                TAG_GLOBAL_FONT_REGULAR_SMALL,
                layout.size_small,
                FontResource.REGULAR,
            ),
            Font.REGULAR_LARGE: FontData(
                TAG_GLOBAL_FONT_REGULAR_LARGE,
                layout.size_large,
                FontResource.REGULAR,
            ),
            Font.ITALIC: FontData(
                TAG_GLOBAL_FONT_ITALIC,
                layout.size,
                FontResource.ITALIC,
            ),
            Font.ITALIC_SMALL: FontData(
                TAG_GLOBAL_FONT_ITALIC_SMALL,
                layout.size_small,
                FontResource.ITALIC,
            ),
            Font.ITALIC_LARGE: FontData(
                TAG_GLOBAL_FONT_ITALIC_LARGE,
                layout.size_large,
                FontResource.ITALIC,
            ),
            Font.BOLD: FontData(
                TAG_GLOBAL_FONT_BOLD,
                layout.size,
                FontResource.BOLD,
            ),
            Font.BOLD_SMALL: FontData(
                TAG_GLOBAL_FONT_BOLD_SMALL,
                layout.size_small,
                FontResource.BOLD,
            ),
            Font.BOLD_LARGE: FontData(
                TAG_GLOBAL_FONT_BOLD_LARGE,
                layout.size_large,
                FontResource.BOLD,
            ),
            Font.ICON: FontData(
                TAG_GLOBAL_FONT_ICON,
                layout.size_small,
                FontResource.ICON,
            ),
        }

    @classmethod
    def register_fonts(cls, scale: int = 1) -> None:
        with dpg.font_registry():
            for font_data in cls._REGISTRY.values():
                dpg.add_font(
                    get_font_path(font_data.font_resource),
                    font_data.size,
                    tag=font_data.tag,
                )

            dpg.bind_font(TAG_GLOBAL_FONT_REGULAR)

        dpg.set_global_font_scale(scale)

    @classmethod
    def get_font(cls, font: Font) -> FontData:
        return cls._REGISTRY[font]

    @classmethod
    def get_tag(cls, font: Font) -> str:
        return cls.get_font(font).tag

    @classmethod
    def get_size(cls, font: Font) -> int:
        return cls.get_font(font).size

    @classmethod
    def get_resource(cls, font: Font) -> FontResource:
        return cls.get_font(font).font_resource

    @classmethod
    def bind_to_item(cls, item: Optional[Sender], font: Font) -> None:
        if item is not None and dpg.does_item_exist(item):
            dpg.bind_item_font(item, cls.get_tag(font))
