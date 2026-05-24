from enum import StrEnum


class TextType(StrEnum):
    LABEL = "label"
    HINT = "hint"
    TITLE = "title"
    MESSAGE = "message"
    FEEDBACK = "feedback"


class Page(StrEnum):
    MAIN = "main"
    RECONSTRUCTIONS = "reconstructions"
    SEQUENCER = "sequencer"
    INSTRUCTIONS = "instructions"
    PROTOTYPE = "prototype"


class Panel(StrEnum):
    PLAYER = "player"
    LIBRARY = "library"
    WAVEFORM = "waveform"
    PAGE = "page"
    LABEL_INPUT = "label_input"
    MULTIPLIER = "multiplier"
    RESULT = "result"
