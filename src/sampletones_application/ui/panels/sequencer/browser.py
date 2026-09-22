from sampletones_application.categories.manager import LanguageManager
from sampletones_application.tags.sequencer import (
    TAG_SEQUENCER_BROWSER_BUTTON_REFRESH_RECONSTRUCTIONS,
    TAG_SEQUENCER_BROWSER_GROUP_CONTROLS,
    TAG_SEQUENCER_BROWSER_GROUP_TREE,
    TAG_SEQUENCER_BROWSER_PANEL,
    TAG_SEQUENCER_BROWSER_TREE,
    TAG_SEQUENCER_BROWSER_WINDOW_TREE,
)
from sampletones_application.ui.elements.tree.tags import FileBrowserTags
from sampletones_application.ui.panels.shared.browser import (
    GUIReconstructionBrowserPanel,
)
from sampletones_core.structures.tree import FileSystemNode


class GUISequencerBrowserPanel(GUIReconstructionBrowserPanel):
    """The Sequencer tab's browser, whose reconstructions become the song's samples."""

    _language_manager: LanguageManager
    _tags: FileBrowserTags = FileBrowserTags(
        panel=TAG_SEQUENCER_BROWSER_PANEL,
        tree=TAG_SEQUENCER_BROWSER_TREE,
        window_tree=TAG_SEQUENCER_BROWSER_WINDOW_TREE,
        group_tree=TAG_SEQUENCER_BROWSER_GROUP_TREE,
        group_controls=TAG_SEQUENCER_BROWSER_GROUP_CONTROLS,
        button_refresh=TAG_SEQUENCER_BROWSER_BUTTON_REFRESH_RECONSTRUCTIONS,
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
