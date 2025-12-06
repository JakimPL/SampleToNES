from typing import Dict

import dearpygui.dearpygui as dpg

from sampletones.typehints import Sender

from ...constants import (
    CHR_STAR,
    TAG_FONT_BOLD,
    TAG_FONT_BOLD_SMALL,
    TAG_FONT_ICON,
    TAG_FONT_REGULAR,
    TAG_FONT_REGULAR_SMALL,
    VAL_FONT_SIZE,
    VAL_FONT_SMALL_SIZE,
    VAL_GLOBAL_FONT_SCALE,
)
from ...resources.items import FontResource
from ...resources.resources import get_font_path
from .data import FontData
from .font import Font


class FontRegistry:
    REGISTRY: Dict[Font, FontData] = {
        Font.REGULAR: FontData(TAG_FONT_REGULAR, VAL_FONT_SIZE, FontResource.REGULAR),
        Font.BOLD: FontData(TAG_FONT_BOLD, VAL_FONT_SIZE, FontResource.BOLD),
        Font.REGULAR_SMALL: FontData(TAG_FONT_REGULAR_SMALL, VAL_FONT_SMALL_SIZE, FontResource.REGULAR),
        Font.BOLD_SMALL: FontData(TAG_FONT_BOLD_SMALL, VAL_FONT_SMALL_SIZE, FontResource.BOLD),
        Font.ICON: FontData(TAG_FONT_ICON, VAL_FONT_SMALL_SIZE, FontResource.ICON),
    }

    @staticmethod
    def register_fonts() -> None:
        with dpg.font_registry():
            dpg.add_font(get_font_path(FontResource.REGULAR), VAL_FONT_SIZE, tag=TAG_FONT_REGULAR)
            dpg.add_font(get_font_path(FontResource.REGULAR), VAL_FONT_SMALL_SIZE, tag=TAG_FONT_REGULAR_SMALL)
            dpg.add_font(get_font_path(FontResource.BOLD), VAL_FONT_SIZE, tag=TAG_FONT_BOLD)
            dpg.add_font(get_font_path(FontResource.BOLD), VAL_FONT_SMALL_SIZE, tag=TAG_FONT_BOLD_SMALL)

            icon_font = dpg.add_font(get_font_path(FontResource.ICON), VAL_FONT_SMALL_SIZE, tag=TAG_FONT_ICON)
            dpg.add_font_range_hint(dpg.mvFontRangeHint_Default, parent=icon_font)
            dpg.add_font_chars([CHR_STAR], parent=icon_font)

            dpg.bind_font(TAG_FONT_REGULAR)

        dpg.set_global_font_scale(VAL_GLOBAL_FONT_SCALE)

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
    def bind_to_item(cls, item: Sender, font: Font) -> None:
        dpg.bind_item_font(item, cls.get_tag(font))
