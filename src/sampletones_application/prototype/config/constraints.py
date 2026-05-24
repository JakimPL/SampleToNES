from pydantic import BaseModel


class LabelInputConstraints(BaseModel, frozen=True):
    max_length: int


class MultiplierConstraints(BaseModel, frozen=True):
    min_value: int
    max_value: int
    default_value: int


class PrototypeConstraints(BaseModel, frozen=True):
    label_input: LabelInputConstraints
    multiplier: MultiplierConstraints
