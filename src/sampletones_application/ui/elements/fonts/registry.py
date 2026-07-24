from typing import Dict, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.layout.fonts import FontsLayout, Step, Typeface
from sampletones_application.tags.general import (
    TAG_GLOBAL_FONT_BOLD,
    TAG_GLOBAL_FONT_BOLD_LARGE,
    TAG_GLOBAL_FONT_BOLD_SMALL,
    TAG_GLOBAL_FONT_ICON,
    TAG_GLOBAL_FONT_ITALIC,
    TAG_GLOBAL_FONT_ITALIC_LARGE,
    TAG_GLOBAL_FONT_ITALIC_SMALL,
    TAG_GLOBAL_FONT_MONO,
    TAG_GLOBAL_FONT_MONO_BOLD,
    TAG_GLOBAL_FONT_MONO_BOLD_SMALL,
    TAG_GLOBAL_FONT_MONO_SMALL,
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
    _REGISTRY: Dict[Font, FontData] = {}
    _SPECS: Dict[Font, Tuple[str, FontResource, Typeface, Step]] = {
        Font.REGULAR: (TAG_GLOBAL_FONT_REGULAR, FontResource.REGULAR, Typeface.SANS, Step.MEDIUM),
        Font.REGULAR_SMALL: (TAG_GLOBAL_FONT_REGULAR_SMALL, FontResource.REGULAR, Typeface.SANS, Step.SMALL),
        Font.REGULAR_LARGE: (TAG_GLOBAL_FONT_REGULAR_LARGE, FontResource.REGULAR, Typeface.SANS, Step.LARGE),
        Font.ITALIC: (TAG_GLOBAL_FONT_ITALIC, FontResource.ITALIC, Typeface.SANS, Step.MEDIUM),
        Font.ITALIC_SMALL: (TAG_GLOBAL_FONT_ITALIC_SMALL, FontResource.ITALIC, Typeface.SANS, Step.SMALL),
        Font.ITALIC_LARGE: (TAG_GLOBAL_FONT_ITALIC_LARGE, FontResource.ITALIC, Typeface.SANS, Step.LARGE),
        Font.BOLD: (TAG_GLOBAL_FONT_BOLD, FontResource.BOLD, Typeface.SANS, Step.MEDIUM),
        Font.BOLD_SMALL: (TAG_GLOBAL_FONT_BOLD_SMALL, FontResource.BOLD, Typeface.SANS, Step.SMALL),
        Font.BOLD_LARGE: (TAG_GLOBAL_FONT_BOLD_LARGE, FontResource.BOLD, Typeface.SANS, Step.LARGE),
        Font.MONO: (TAG_GLOBAL_FONT_MONO, FontResource.MONO, Typeface.MONO, Step.MEDIUM),
        Font.MONO_SMALL: (TAG_GLOBAL_FONT_MONO_SMALL, FontResource.MONO, Typeface.MONO, Step.SMALL),
        Font.MONO_BOLD: (TAG_GLOBAL_FONT_MONO_BOLD, FontResource.MONO_BOLD, Typeface.MONO, Step.MEDIUM),
        Font.MONO_BOLD_SMALL: (TAG_GLOBAL_FONT_MONO_BOLD_SMALL, FontResource.MONO_BOLD, Typeface.MONO, Step.SMALL),
        Font.ICON: (TAG_GLOBAL_FONT_ICON, FontResource.ICON, Typeface.ICON, Step.SMALL),
    }

    @classmethod
    def setup(cls, layout: FontsLayout) -> None:
        cls._REGISTRY = {
            font: FontData(tag, layout.size_for(typeface, step), resource)
            for font, (tag, resource, typeface, step) in cls._SPECS.items()
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
