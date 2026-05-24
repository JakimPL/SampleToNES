from typing import Callable, Optional

from sampletones_shared.utils.callbacks import CallbackMixin

from ..models.score import ScoreResultViewModel


class ScoreLogic(CallbackMixin):
    def __init__(self, default_multiplier: int) -> None:
        self._current_label: str = ""
        self._current_multiplier: int = default_multiplier
        self.on_result: Optional[Callable[[ScoreResultViewModel], None]] = None

    def update_label(self, label: str) -> None:
        self._current_label = label
        self._emit()

    def update_multiplier(self, multiplier: int) -> None:
        self._current_multiplier = multiplier
        self._emit()

    def _emit(self) -> None:
        stripped = self._current_label.strip()
        if not stripped:
            return
        score = len(stripped) * self._current_multiplier
        result_text = f'"{self._current_label}" \u00d7 {self._current_multiplier} = {score}'
        self.call(self.on_result, ScoreResultViewModel(result_text=result_text, score=score))
