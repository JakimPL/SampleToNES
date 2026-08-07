from pydantic import BaseModel

from sampletones_application.layout.general.dialogs.height import DialogSizeNoWidth
from sampletones_application.layout.primitives import Dimensions


class DialogsLayout(BaseModel, extra="forbid", frozen=True):
    default: Dimensions
    error: Dimensions
    recovery: Dimensions
    confirmation: DialogSizeNoWidth
    text_input: DialogSizeNoWidth
    traceback: Dimensions
