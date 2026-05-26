from pydantic import BaseModel


class InstructionPanelViewModel(BaseModel, frozen=True):
    is_loaded: bool
