from sampletones_application.text.hierarchy import Page, Panel, Widget
from sampletones_application.text.key import TagName

TAG_PANEL_SEQUENCER_BROWSER = TagName(Page.SEQUENCER, Panel.BROWSER, Widget.PANEL, "browser")
TAG_TREE_SEQUENCER_BROWSER = TagName(Page.SEQUENCER, Panel.BROWSER, Widget.TREE, "browser")
TAG_GROUP_SEQUENCER_BROWSER_TREE = TagName(Page.SEQUENCER, Panel.BROWSER, Widget.GROUP, "tree")
TAG_WINDOW_SEQUENCER_BROWSER_TREE = TagName(Page.SEQUENCER, Panel.BROWSER, Widget.WINDOW, "tree")
TAG_GROUP_SEQUENCER_BROWSER_CONTROLS = TagName(Page.SEQUENCER, Panel.BROWSER, Widget.GROUP, "controls")
TAG_BUTTON_SEQUENCER_BROWSER_REFRESH_RECONSTRUCTIONS = TagName(
    Page.SEQUENCER, Panel.BROWSER, Widget.BUTTON, "refresh_reconstructions"
)

TAG_PANEL_SEQUENCER_GRID = TagName(Page.SEQUENCER, Panel.GRID, Widget.PANEL, "grid")
TAG_PANEL_SEQUENCER_GRID_PLAYER = TagName(Page.SEQUENCER, Panel.GRID, Widget.PANEL, "grid_player")
TAG_GROUP_SEQUENCER_GRID_MODULE_OPTIONS = TagName(Page.SEQUENCER, Panel.GRID, Widget.GROUP, "module_options")
TAG_INPUT_SEQUENCER_GRID_NES_FREQUENCY = TagName(Page.SEQUENCER, Panel.GRID, Widget.INPUT, "nes_frequency")
TAG_INPUT_SEQUENCER_GRID_TEMPO = TagName(Page.SEQUENCER, Panel.GRID, Widget.INPUT, "tempo")
TAG_INPUT_SEQUENCER_GRID_SPEED = TagName(Page.SEQUENCER, Panel.GRID, Widget.INPUT, "speed")
TAG_BUTTON_SEQUENCER_GRID_EXPORT_MODULE = TagName(Page.SEQUENCER, Panel.GRID, Widget.BUTTON, "export_module")
TAG_TABLE_SEQUENCER_GRID_TRACKER = TagName(Page.SEQUENCER, Panel.GRID, Widget.TABLE, "tracker")
TAG_WINDOW_SEQUENCER_GRID_TRACKER = TagName(Page.SEQUENCER, Panel.GRID, Widget.WINDOW, "tracker")
TAG_PANEL_SEQUENCER_SAMPLES = TagName(Page.SEQUENCER, Panel.INSTRUMENTS, Widget.PANEL, "instruments")
TAG_TABLE_SEQUENCER_SAMPLES = TagName(Page.SEQUENCER, Panel.INSTRUMENTS, Widget.TABLE, "instruments")
TAG_WINDOW_SEQUENCER_SAMPLES = TagName(Page.SEQUENCER, Panel.INSTRUMENTS, Widget.WINDOW, "instruments")
TAG_THEME_TABLE_PATTERN = TagName(Page.SEQUENCER, Panel.IMPLICIT, Widget.THEME, "table_pattern")
