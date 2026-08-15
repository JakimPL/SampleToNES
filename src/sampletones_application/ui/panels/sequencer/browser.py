from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.behavior.scheduling.scheduling import (
    SchedulingBehavior,
)
from sampletones_application.tags.sequencer import (
    TAG_SEQUENCER_BROWSER_BUTTON_REFRESH_RECONSTRUCTIONS,
    TAG_SEQUENCER_BROWSER_GROUP_CONTROLS,
    TAG_SEQUENCER_BROWSER_GROUP_TREE,
    TAG_SEQUENCER_BROWSER_PANEL,
    TAG_SEQUENCER_BROWSER_TREE,
    TAG_SEQUENCER_BROWSER_WINDOW_TREE,
)
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.elements.tree.colors import TreeColors
from sampletones_application.ui.elements.tree.protocol import TreeLogicProtocol
from sampletones_application.ui.panels.shared.browser import (
    GUIReconstructionBrowserPanel,
)
from sampletones_core.structures.tree import FileSystemNode, Tree


class GUISequencerBrowserPanel(GUIReconstructionBrowserPanel):
    _panel_tag = TAG_SEQUENCER_BROWSER_PANEL
    _tree_tag = TAG_SEQUENCER_BROWSER_TREE
    _button_refresh_tag = TAG_SEQUENCER_BROWSER_BUTTON_REFRESH_RECONSTRUCTIONS
    _group_controls_tag = TAG_SEQUENCER_BROWSER_GROUP_CONTROLS
    _group_tree_tag = TAG_SEQUENCER_BROWSER_GROUP_TREE
    _window_tree_tag = TAG_SEQUENCER_BROWSER_WINDOW_TREE

    def __init__(
        self,
        tree: Tree,
        tree_logic: TreeLogicProtocol,
        *,
        scheduling: SchedulingBehavior,
        language_manager: LanguageManager,
        status_bar: GUIStatusBar,
        colors: TreeColors,
        initial_collapsed: bool = False,
    ) -> None:
        super().__init__(
            tree=tree,
            tree_logic=tree_logic,
            scheduling=scheduling,
            language_manager=language_manager,
            status_bar=status_bar,
            colors=colors,
            reconstructions_label=language_manager["sequencer.browser.label.reconstructions_tree"],
            refresh_button_label=language_manager["sequencer.browser.label.refresh_button"],
            refresh_status_message=language_manager["sequencer.browser.message.status_refresh"],
            initial_collapsed=initial_collapsed,
        )

    def _open_reconstruction(self, node: FileSystemNode) -> None:
        self._logic.cancel_autoplay()
        self.call(self.on_add_to_sequencer, node.filepath)

    def _add_reconstruction_context_menu_items(self, node: FileSystemNode) -> None:
        self._add_context_menu_sequencer_items(node)
        self._add_context_menu_replace_item(node)
