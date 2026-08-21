from pydantic import BaseModel

from sampletones_application.layout.primitives import Dimensions


class ConverterLayout(BaseModel, extra="forbid", frozen=True):
    width: int
    height: int
    button_height: int
    stems_list_height: int
    cap_input_width: int
    hierarchy_combo_width: int
    level_input_width: int
    remove_button_width: int
    stem_selection: Dimensions
