from enum import StrEnum


class TextType(StrEnum):
    LABEL = "label"
    HINT = "hint"
    TITLE = "title"
    MESSAGE = "message"
    FEEDBACK = "feedback"
    TEMPLATE = "template"
    TOOLTIP = "tooltip"


class Widget(StrEnum):
    BUTTON = "button"
    CHECKBOX = "checkbox"
    COMBO = "combo"
    DIALOG = "dialog"
    FONT = "font"
    GROUP = "group"
    HANDLER = "handler"
    HEADER = "header"
    INPUT = "input"
    MENU = "menu"
    PANEL = "panel"
    PATH = "path"
    PROGRESS = "progress"
    SLIDER = "slider"
    STATUS = "status"
    TAB = "tab"
    TABLE = "table"
    TABS = "tabs"
    TEXT = "text"
    THEME = "theme"
    TREE = "tree"
    WINDOW = "window"


class Page(StrEnum):
    GLOBAL = "global"
    MAIN = "main"
    RECONSTRUCTIONS = "reconstructions"
    SEQUENCER = "sequencer"
    INSTRUCTIONS = "instructions"
    SETTINGS = "settings"
    PROTOTYPE = "prototype"


class Tab(StrEnum):
    MAIN = "tab_main"
    RECONSTRUCTIONS = "tab_reconstructions"
    SEQUENCER = "tab_sequencer"
    INSTRUCTIONS = "tab_instructions"


class Panel(StrEnum):
    # Implicit panel (no panel in tag hierarchy, omitted from string representation)
    IMPLICIT = ""

    # Global cross-page panels
    MENU = "menu"
    DIALOG = "dialog"
    TRACEBACK = "traceback"
    CONTEXT = "context"
    STATUS = "status"
    GRAPH = "graph"

    # Shared per-page panels (used under multiple Pages)
    PLAYER = "player"
    BROWSER = "browser"
    DETAILS = "details"
    EXPLORER = "explorer"

    # Main tab
    CONFIG_PANEL = "config_panel"
    RECONSTRUCTOR = "reconstructor"
    CONVERTER = "converter"
    ADVANCED = "advanced"

    # Reconstructions tab
    RECONSTRUCTION = "reconstruction"

    # Sequencer tab
    GRID = "grid"
    INSTRUMENTS = "instruments"

    # Instructions tab
    LIBRARY = "library"
    INSTRUCTION = "instruction"

    # Settings
    AUDIO = "audio"

    # Prototype
    PAGE = "page"
    LABEL_INPUT = "label_input"
    MULTIPLIER = "multiplier"
    RESULT = "result"
