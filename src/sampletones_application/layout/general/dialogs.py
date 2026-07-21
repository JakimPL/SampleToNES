from pydantic import BaseModel

from sampletones_application.layout.primitives import Dimensions


class DialogSizeNoWidth(BaseModel, extra="forbid", frozen=True):
    height: int


class DialogsLayout(BaseModel, extra="forbid", frozen=True):
    default: Dimensions
    error: Dimensions
    recovery: Dimensions
    confirmation: DialogSizeNoWidth
    text_input: DialogSizeNoWidth
    traceback: Dimensions
