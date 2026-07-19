from pydantic import BaseModel


class DialogSizeLayout(BaseModel, extra="forbid", frozen=True):
    width: int
    height: int


class DialogSizeNoWidth(BaseModel, extra="forbid", frozen=True):
    height: int


class DialogsLayout(BaseModel, extra="forbid", frozen=True):
    default: DialogSizeLayout
    error: DialogSizeLayout
    recovery: DialogSizeLayout
    confirmation: DialogSizeNoWidth
    text_input: DialogSizeNoWidth
    traceback: DialogSizeLayout
