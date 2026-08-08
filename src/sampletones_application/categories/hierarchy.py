from enum import StrEnum, auto


class TextType(StrEnum):
    LABEL = "label"
    TITLE = "title"
    MESSAGE = "message"
    TEMPLATE = "template"
    TOOLTIP = "tooltip"
    FILTER = "filter"


class Widget(StrEnum):
    BUTTON = "button"
    CHECKBOX = "checkbox"
    COMBO = "combo"
    DIALOG = "dialog"
    FONT = "font"
    GROUP = "group"
    HEADER = "header"
    INPUT = "input"
    MENU = "menu"
    PANEL = "panel"
    PATH = "path"
    PROGRESS = "progress"
    RADIO = "radio"
    SLIDER = "slider"
    STATUS = "status"
    TAB = "tab"
    TABLE = "table"
    TABS = "tabs"
    TEXT = "text"
    THEME = "theme"
    TOOLTIP = "tooltip"
    TREE = "tree"
    WINDOW = "window"


class Page(StrEnum):
    GLOBAL = "global"
    MAIN = "main"
    RECONSTRUCTIONS = "reconstructions"
    SEQUENCER = "sequencer"
    INSTRUCTIONS = "instructions"
    SETTINGS = "settings"


class Tab(StrEnum):
    MAIN = "main"
    RECONSTRUCTIONS = "reconstructions"
    SEQUENCER = "sequencer"
    INSTRUCTIONS = "instructions"


class Panel(StrEnum):
    IMPLICIT = ""

    # Global cross-page panels
    MENU = auto()
    DIALOG = auto()
    TRACEBACK = auto()
    CONTEXT = auto()
    STATUS = auto()
    GRAPH = auto()
    PITCH = auto()

    # Shared per-page panels (used under multiple Pages)
    PLAYER = auto()
    BROWSER = auto()
    DETAILS = auto()
    EXPLORER = auto()

    # Main tab
    CONFIG = auto()
    RECONSTRUCTOR = auto()
    CONVERTER = auto()
    ADVANCED = auto()

    # Reconstructions tab
    RECONSTRUCTION = auto()

    # Sequencer tab
    TRACKER = auto()
    ORDER = auto()
    MODULE = auto()
    INSTRUMENTS = auto()
    HISTORY = auto()

    # Instructions tab
    LIBRARY = auto()
    INSTRUCTION = auto()

    # Settings
    AUDIO = auto()
    DISPLAY = auto()
    PROPERTIES = auto()
