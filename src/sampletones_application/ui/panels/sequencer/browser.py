from typing import AbstractSet

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
from sampletones_application.ui.elements.tree.tags import FileBrowserTags
from sampletones_application.ui.panels.shared.browser import (
    GUIReconstructionBrowserPanel,
)
from sampletones_core.structures.tree import FileSystemNode, Tree


class GUISequencerBrowserPanel(GUIReconstructionBrowserPanel):
    """The Sequencer tab's browser, whose reconstructions become the song's samples."""

    _tags: FileBrowserTags = FileBrowserTags(
        panel=TAG_SEQUENCER_BROWSER_PANEL,
        tree=TAG_SEQUENCER_BROWSER_TREE,
        window_tree=TAG_SEQUENCER_BROWSER_WINDOW_TREE,
        group_tree=TAG_SEQUENCER_BROWSER_GROUP_TREE,
        group_controls=TAG_SEQUENCER_BROWSER_GROUP_CONTROLS,
        button_refresh=TAG_SEQUENCER_BROWSER_BUTTON_REFRESH_RECONSTRUCTIONS,
    )

    def __init__(
        self,
        tree: Tree,
        tree_logic: TreeLogicProtocol,
        *,
        scheduling: SchedulingBehavior,
        language_manager: LanguageManager,
        status_bar: GUIStatusBar,
        colors: TreeColors,
        initial_collapsed: bool,
        initial_favorites_only: bool,
        initial_expanded_rows: AbstractSet[str],
    ) -> None:
        self._language_manager = language_manager

        super().__init__(
            tree=tree,
            tree_logic=tree_logic,
            scheduling=scheduling,
            language_manager=language_manager,
            status_bar=status_bar,
            colors=colors,
            initial_collapsed=initial_collapsed,
            initial_favorites_only=initial_favorites_only,
            initial_expanded_rows=initial_expanded_rows,
        )

    @property
    def refresh_button_label(self) -> str:
        return self._language_manager["sequencer.browser.label.refresh_button"]

    @property
    def refresh_status_message(self) -> str:
        return self._language_manager["sequencer.browser.message.status_refresh"]

    def _open_reconstruction(self, node: FileSystemNode) -> None:
        self.call(self.on_add_to_sequencer, node.filepath)

    def _add_reconstruction_context_menu_items(self, node: FileSystemNode) -> None:
        self._add_context_menu_sequencer_items(node)
        self._add_context_menu_replace_item(node)
