from sampletones_application.ui.resources.items import FontResource, IconResource
from sampletones_application.ui.resources.loader import ResourceLoader
from sampletones_core.constants.paths import FONT_DIRECTORY, ICON_DIRECTORY

icon_loader = ResourceLoader(ICON_DIRECTORY)
font_loader = ResourceLoader(FONT_DIRECTORY)


def get_icon_path(icon_name: IconResource) -> str:
    return icon_loader.get_path(icon_name.value)


def get_icon_bytes(icon_name: IconResource) -> bytes:
    return icon_loader.get_bytes(icon_name.value)


def get_font_path(font_name: FontResource) -> str:
    return font_loader.get_path(font_name.value)


def get_font_bytes(font_name: FontResource) -> bytes:
    return font_loader.get_bytes(font_name.value)
