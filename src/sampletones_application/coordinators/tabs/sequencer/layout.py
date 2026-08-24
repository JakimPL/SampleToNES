import dearpygui.dearpygui as dpg

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.config.managers.session import SessionManager
from sampletones_application.parameters.sequencer import SequencerTabParameters
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import (
    SUF_PANEL_CENTER,
    SUF_PANEL_LEFT,
    SUF_PANEL_RIGHT,
    TAG_GLOBAL_TAB_SEQUENCER,
    TAG_GLOBAL_TABS,
    TAG_GLOBAL_THEME_DEFAULT,
    TAG_GLOBAL_THEME_PANEL_GROUND,
    TAG_GLOBAL_THEME_PANEL_SURFACE,
)
from sampletones_application.tags.sequencer import TAG_SEQUENCER_HISTORY_PANEL
from sampletones_application.ui.elements.layout.columns import ColumnSpec, TabColumns
from sampletones_application.ui.elements.layout.responsive import expanded_side_width
from sampletones_application.ui.panels.sequencer.browser import GUISequencerBrowserPanel
from sampletones_application.ui.panels.sequencer.history import GUISequencerHistoryPanel
from sampletones_application.ui.panels.sequencer.module import GUISequencerModulePanel
from sampletones_application.ui.panels.sequencer.order.panel import GUISequencerOrderPanel
from sampletones_application.ui.panels.sequencer.tracker.panel import GUISequencerTrackerPanel
from sampletones_application.ui.panels.sequencer.voices.panel import GUISequencerVoicesPanel
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.gui.dpg import dpg_configure_item

LEFT_COLUMN_TAG = compose_tag(TAG_GLOBAL_TAB_SEQUENCER, SUF_PANEL_LEFT)
CENTER_COLUMN_TAG = compose_tag(TAG_GLOBAL_TAB_SEQUENCER, SUF_PANEL_CENTER)
RIGHT_COLUMN_TAG = compose_tag(TAG_GLOBAL_TAB_SEQUENCER, SUF_PANEL_RIGHT)


class SequencerTabLayout:
    """The three columns this tab stands in, and how they refit as the window and cards change.

    The browser fills the left column, the two grids stack down the center, and the module,
    samples and history cards stack down the right. A column keeps its share of the viewport as
    the window is resized, and a card that collapses hands its space back to the card above it.

    Each collapse is written to the session as it happens, so the tab opens next launch showing
    exactly the cards it was left showing.
    """

    def __init__(
        self,
        browser_panel: GUISequencerBrowserPanel,
        order_panel: GUISequencerOrderPanel,
        tracker_panel: GUISequencerTrackerPanel,
        module_panel: GUISequencerModulePanel,
        voices_panel: GUISequencerVoicesPanel,
        history_panel: GUISequencerHistoryPanel,
        *,
        layout: SequencerTabParameters,
        session_manager: SessionManager,
        language_manager: LanguageManager,
    ) -> None:
        self._browser_panel = browser_panel
        self._order_panel = order_panel
        self._tracker_panel = tracker_panel
        self._module_panel = module_panel
        self._voices_panel = voices_panel
        self._history_panel = history_panel
        self._session_manager = session_manager
        self._language_manager = language_manager
        self._geometry = layout.geometry
        self._side_panel_count: int
        self._instruments_width = layout.right_column_width
        self._right_height = layout.right_column_height
        self._history_expanded_height = layout.history_height
        self._history_collapsed_footprint = layout.header_bar_height + 2 * self._geometry.panel_gap
        self._inter_card_gap = self._stacked_card_gap()

    def create_tab(self) -> None:
        """Builds the tab and the three columns its panels are drawn into."""
        with dpg.tab(
            tag=TAG_GLOBAL_TAB_SEQUENCER,
            parent=TAG_GLOBAL_TABS,
            label=self._language_manager["global.menu.label.tab_sequencer"],
        ):
            self._side_panel_count = TabColumns.build(
                panel_gap=self._geometry.panel_gap,
                columns=[
                    ColumnSpec(
                        tag=LEFT_COLUMN_TAG,
                        build=self._browser_panel.create_panel,
                        theme=TAG_GLOBAL_THEME_PANEL_SURFACE,
                        width=self._geometry.side_width,
                        height=self._geometry.side_height,
                        no_scrollbar=True,
                    ),
                    ColumnSpec(
                        tag=CENTER_COLUMN_TAG,
                        build=self._build_center_column,
                        theme=TAG_GLOBAL_THEME_PANEL_GROUND,
                        border=False,
                    ),
                    ColumnSpec(
                        tag=RIGHT_COLUMN_TAG,
                        build=self._build_right_column,
                        theme=TAG_GLOBAL_THEME_PANEL_GROUND,
                        width=self._instruments_width,
                        height=self._right_height,
                        border=False,
                        no_scrollbar=True,
                    ),
                ],
            )

        self._sync_browser_width()

    def sync_responsive_layout(self) -> None:
        """Refits this tab's side column to the current viewport, the entry the resize handler calls."""
        self._sync_browser_width()

    def on_card_collapse_changed(self, card_tag: str, collapsed: bool) -> None:
        """Persists a card's collapsed state so it restores on the next launch."""
        self._session_manager.set_card_collapsed(card_tag, collapsed)
        if card_tag == TAG_SEQUENCER_HISTORY_PANEL:
            self._sync_voices_height()

    def on_browser_collapse_changed(self, card_tag: str, collapsed: bool) -> None:
        """Persists the browser panel's collapse, then docks or restores the width of the column it fills."""
        self._session_manager.set_card_collapsed(card_tag, collapsed)
        self._sync_browser_width()

    def on_browser_favorites_filter_changed(self, panel_tag: str, favorites_only: bool) -> None:
        """Persists the browser's favorites filter so it opens in the same mode on the next launch."""
        self._session_manager.set_favorites_filter_active(panel_tag, favorites_only)

    def _build_center_column(self, parent: str) -> None:
        """Stacks the order table and tracker tracker down the center column."""
        self._order_panel.create_panel(parent)
        dpg.add_spacer(height=self._geometry.panel_gap, parent=parent)
        self._tracker_panel.create_panel(parent)

    def _build_right_column(self, parent: str) -> None:
        """Stacks the module settings, samples, and history cards in the right column."""
        self._module_panel.create_panel(parent)
        dpg.add_spacer(height=self._geometry.panel_gap)
        self._voices_panel.create_panel(parent)
        dpg.add_spacer(height=self._geometry.panel_gap)
        self._history_panel.create_panel(parent)
        self._sync_voices_height()

    def _sync_browser_width(self) -> None:
        """Shrinks the browser column to the collapse rail when collapsed, else sizes it to the viewport width."""
        if self._browser_panel.collapsed:
            width = self._geometry.rail_width
        else:
            width = expanded_side_width(
                self._geometry.side_width,
                dpg.get_viewport_client_width(),
                self._geometry.baseline_viewport_width,
                self._side_panel_count,
                self._geometry.center_weight,
            )

        dpg_configure_item(LEFT_COLUMN_TAG, width=width)

    def _stacked_card_gap(self) -> int:
        """The rendered vertical gap between two cards stacked in the right column.

        The cards are separated by a ``panel_gap`` spacer, but DearPyGui also lays its ``ItemSpacing.y``
        on each side of that spacer, so the real gap is the spacer plus two of those spacings. The
        spacing is read from the base theme, which sets it explicitly, so the gap tracks the theme's
        value.
        """
        spacing = ThemeRegistry.get(TAG_GLOBAL_THEME_DEFAULT).get_style(
            dpg.mvAll,
            dpg.mvStyleVar_ItemSpacing,
        )
        spacing_y = int(spacing[1]) if spacing is not None else 0
        return self._geometry.panel_gap + 2 * spacing_y

    def _sync_voices_height(self) -> None:
        """Reserves the bottom space the history card and its inter-card gap occupy, so samples fills the rest.

        The samples card fills the right column above the history card by reserving that footprint below
        it. History carries its own height in both states — filling the reservation while expanded, pinned
        to its header bar while collapsed — so this only has to size the reservation: the expanded history
        height, or the collapsed bar footprint. The reservation clears the full inter-card gap (see
        :meth:`_stacked_card_gap`) so the collapsed bar lands flush at the column bottom.
        """
        if self._history_panel.collapsed:
            footprint = self._history_collapsed_footprint
        else:
            footprint = self._history_expanded_height

        self._voices_panel.set_expanded_height(-(self._inter_card_gap + footprint))
