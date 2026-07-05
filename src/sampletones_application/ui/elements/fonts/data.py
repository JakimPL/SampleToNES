from typing import NamedTuple

from sampletones_application.ui.resources.items import FontResource


class FontData(NamedTuple):
    tag: str
    size: int
    font_resource: FontResource
