from typing import ClassVar, Dict

import dearpygui.dearpygui as dpg

from sampletones_application.tags.general import TAG_GLOBAL_TEXTURE_LOGO
from sampletones_application.ui.resources.items import IconResource
from sampletones_application.ui.resources.resources import get_icon_path


class TextureRegistry:
    """Reads the images the interface draws into DearPyGui textures, the once at startup.

    A texture is created before any window asks for it and stands for the whole run, so whatever draws
    the application's mark names it by the tag it was created under.
    """

    _IMAGES: ClassVar[Dict[str, IconResource]] = {
        TAG_GLOBAL_TEXTURE_LOGO: IconResource.UNIX,
    }

    @classmethod
    def register_textures(cls) -> None:
        with dpg.texture_registry():
            for tag, resource in cls._IMAGES.items():
                width, height, _channels, data = dpg.load_image(get_icon_path(resource))
                dpg.add_static_texture(width, height, data, tag=tag)
