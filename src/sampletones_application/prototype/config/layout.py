from pydantic import BaseModel


class ViewportLayout(BaseModel, frozen=True):
    width: int
    height: int


class LabelInputLayout(BaseModel, frozen=True):
    panel_width: int
    panel_height: int
    input_width: int


class MultiplierLayout(BaseModel, frozen=True):
    panel_width: int
    panel_height: int
    slider_width: int


class ResultLayout(BaseModel, frozen=True):
    panel_height: int


class PrototypeLayout(BaseModel, frozen=True):
    viewport: ViewportLayout
    label_input: LabelInputLayout
    multiplier: MultiplierLayout
    result: ResultLayout
