from typing import Callable, Optional

from sampletones_application.prototype.config.constraints import LabelInputConstraints
from sampletones_application.prototype.models.label_input import LabelValidationViewModel
from sampletones_application.prototype.text.elements import LabelInputElements
from sampletones_application.text.hierarchy import Page, Panel, TextType
from sampletones_application.text.key import TextKey
from sampletones_application.text.manager import LanguageManager
from sampletones_shared.utils.callbacks import CallbackMixin

_KEY_FEEDBACK_EMPTY = TextKey(Page.PROTOTYPE, Panel.LABEL_INPUT, TextType.FEEDBACK, LabelInputElements.VALIDATION_EMPTY)
_KEY_FEEDBACK_TOO_LONG = TextKey(
    Page.PROTOTYPE, Panel.LABEL_INPUT, TextType.FEEDBACK, LabelInputElements.VALIDATION_TOO_LONG
)


class LabelValidationLogic(CallbackMixin):
    def __init__(self, lang: LanguageManager, constraints: LabelInputConstraints) -> None:
        self._lang = lang
        self._max_length = constraints.max_length
        self.on_validation_changed: Optional[Callable[[LabelValidationViewModel], None]] = None

    def update(self, label: str) -> None:
        self.call(self.on_validation_changed, self._validate(label))

    def _validate(self, label: str) -> LabelValidationViewModel:
        if not label.strip():
            return LabelValidationViewModel(is_valid=False, message=self._lang[_KEY_FEEDBACK_EMPTY])
        if len(label) > self._max_length:
            return LabelValidationViewModel(
                is_valid=False,
                message=self._lang[_KEY_FEEDBACK_TOO_LONG].format(self._max_length),
            )
        return LabelValidationViewModel(is_valid=True, message="")
