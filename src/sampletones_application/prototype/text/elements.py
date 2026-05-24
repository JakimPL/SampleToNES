from sampletones_application.text.abstract import AbstractElement


class PrototypePageElements(AbstractElement):
    WINDOW_TITLE = "window_title"


class LabelInputElements(AbstractElement):
    SECTION_HEADER = "section_header"
    INPUT = "input"
    VALIDATION_EMPTY = "validation_empty"
    VALIDATION_TOO_LONG = "validation_too_long"


class MultiplierElements(AbstractElement):
    SECTION_HEADER = "section_header"
    SLIDER = "slider"


class ResultElements(AbstractElement):
    SECTION_HEADER = "section_header"
    SCORE = "score"
    NO_RESULT = "no_result"
