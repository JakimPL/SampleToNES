from pydantic import BaseModel


class LabelValidationViewModel(BaseModel, frozen=True):
    is_valid: bool
    message: str
