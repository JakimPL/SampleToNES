from typing import Dict, Optional

import dearpygui.dearpygui as dpg

from sampletones.typehints import Sender

from ...constants.general import (
    TAG_FONT_BOLD,
    TAG_FONT_BOLD_LARGE,
    TAG_FONT_BOLD_SMALL,
    TAG_FONT_ICON,
    TAG_FONT_ITALIC,
    TAG_FONT_ITALIC_LARGE,
    TAG_FONT_ITALIC_SMALL,
    TAG_FONT_REGULAR,
    TAG_FONT_REGULAR_LARGE,
    TAG_FONT_REGULAR_SMALL,
    VAL_CHARACTER_STAR,
    VAL_FONT_SCALE,
    VAL_FONT_SIZE,
    VAL_FONT_SIZE_LARGE,
    VAL_FONT_SIZE_SMALL,
)
from ...resources.items import FontResource
from ...resources.resources import get_font_path
from .data import FontData
from .font import Font


class FontRegistry:
    REGISTRY: Dict[Font, FontData] = {
        Font.REGULAR: FontData(TAG_FONT_REGULAR, VAL_FONT_SIZE, FontResource.REGULAR),
        Font.REGULAR_SMALL: FontData(TAG_FONT_REGULAR_SMALL, VAL_FONT_SIZE_SMALL, FontResource.REGULAR),
        Font.REGULAR_LARGE: FontData(TAG_FONT_REGULAR_LARGE, VAL_FONT_SIZE_LARGE, FontResource.REGULAR),
        Font.ITALIC: FontData(TAG_FONT_ITALIC, VAL_FONT_SIZE, FontResource.ITALIC),
        Font.ITALIC_SMALL: FontData(TAG_FONT_ITALIC_SMALL, VAL_FONT_SIZE_SMALL, FontResource.ITALIC),
        Font.ITALIC_LARGE: FontData(TAG_FONT_ITALIC_LARGE, VAL_FONT_SIZE_LARGE, FontResource.ITALIC),
        Font.BOLD: FontData(TAG_FONT_BOLD, VAL_FONT_SIZE, FontResource.BOLD),
        Font.BOLD_SMALL: FontData(TAG_FONT_BOLD_SMALL, VAL_FONT_SIZE_SMALL, FontResource.BOLD),
        Font.BOLD_LARGE: FontData(TAG_FONT_BOLD_LARGE, VAL_FONT_SIZE_LARGE, FontResource.BOLD),
        Font.ICON: FontData(TAG_FONT_ICON, VAL_FONT_SIZE_SMALL, FontResource.ICON),
    }

    @staticmethod
    def register_fonts() -> None:
        with dpg.font_registry():
            for font_data in FontRegistry.REGISTRY.values():
                dpg.add_font(get_font_path(font_data.font_resource), font_data.size, tag=font_data.tag)
                dpg.add_font_range(0x0100, 0x024F, parent=font_data.tag)
                dpg.add_font_range(0x1E00, 0x1EFF, parent=font_data.tag)
                dpg.add_font_range(0x2000, 0x206F, parent=font_data.tag)
                dpg.add_font_range(0x2C60, 0x2C7F, parent=font_data.tag)
                dpg.add_font_range(0xA720, 0xA7FF, parent=font_data.tag)

            dpg.add_font_chars([VAL_CHARACTER_STAR], parent=TAG_FONT_ICON)
            dpg.bind_font(TAG_FONT_REGULAR)

        dpg.set_global_font_scale(VAL_FONT_SCALE)

    @classmethod
    def get_font(cls, font: Font) -> FontData:
        return cls.REGISTRY[font]

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
