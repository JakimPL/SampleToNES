from pydantic import BaseModel


class ScoreResultViewModel(BaseModel, frozen=True):
    result_text: str
    score: int
