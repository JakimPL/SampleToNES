from pydantic import BaseModel

from sampletones_application.layout.primitives import Dimensions


class ConverterLayout(BaseModel, extra="forbid", frozen=True):
    width: int
    button_height: int
    handle_width: int
    channel_column_width: int
    remove_button_width: int
    level_strip_height: int
    stem_selection: Dimensions
    stem_selection_footer: int
