from typing import NamedTuple

from ...resources.items import FontResource


class FontData(NamedTuple):
    tag: str
    size: int
    font_resource: FontResource
