import dearpygui.dearpygui as dpg

from sampletones.typehints import Sender

from ...constants import (
    TAG_FONT_BOLD,
    TAG_FONT_BOLD_SMALL,
    TAG_FONT_REGULAR,
    TAG_FONT_REGULAR_SMALL,
    VAL_FONT_SIZE,
    VAL_FONT_SMALL_SIZE,
    VAL_GLOBAL_FONT_SCALE,
)
from ...resources.items import FontResource
from ...resources.resources import get_font_path
from .font import Font


class FontRegistry:
    REGISTRY = {
        Font.REGULAR: TAG_FONT_REGULAR,
        Font.BOLD: TAG_FONT_BOLD,
        Font.REGULAR_SMALL: TAG_FONT_REGULAR_SMALL,
        Font.BOLD_SMALL: TAG_FONT_BOLD_SMALL,
    }

    @staticmethod
    def register_fonts() -> None:
        with dpg.font_registry():
            dpg.add_font(get_font_path(FontResource.REGULAR), VAL_FONT_SIZE, tag=TAG_FONT_REGULAR)
            dpg.add_font(get_font_path(FontResource.REGULAR), VAL_FONT_SMALL_SIZE, tag=TAG_FONT_REGULAR_SMALL)
            dpg.add_font(get_font_path(FontResource.BOLD), VAL_FONT_SIZE, tag=TAG_FONT_BOLD)
            dpg.add_font(get_font_path(FontResource.BOLD), VAL_FONT_SMALL_SIZE, tag=TAG_FONT_BOLD_SMALL)
            dpg.bind_font(TAG_FONT_REGULAR)

        dpg.set_global_font_scale(VAL_GLOBAL_FONT_SCALE)

    @classmethod
    def get_font(cls, font: Font) -> str:
        return cls.REGISTRY[font]

    @classmethod
    def bind_to_item(cls, item: Sender, font: Font) -> None:
        dpg.bind_item_font(item, cls.get_font(font))
