from typing import Callable, FrozenSet, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.general.stems import StemsListLayout
from sampletones_application.tags.reconstructions import (
    PRE_RECONSTRUCTION_STEMS,
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_CHECKBOX_COLLAPSE_LEVELS,
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_PANEL_STEMS,
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_TEXT_STEMS_EMPTY,
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_TEXT_STEMS_SETUP,
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_TOOLTIP_COLLAPSE_LEVELS,
)
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.elements.stems.list import GUIStemsList
from sampletones_application.utils.gui.dpg import dpg_configure_item, dpg_set_value
from sampletones_application.utils.gui.tooltip import show_tooltip
from sampletones_application.view_model.reconstruction.stems import (
    ReconstructionStemsViewModel,
)
from sampletones_application.view_model.shared.stems import StemsListViewModel
from sampletones_core.constants.enums import ChannelName, HierarchyMode
from sampletones_shared.types.application import Sender
from sampletones_shared.utils.system.paths import open_path_in_explorer

MINIMUM_COLLAPSIBLE_LEVELS: int = 2


class GUIReconstructionStemsPanel(GUIPanel):
    """The recordings a loaded reconstruction was built from, as the stems list draws them.

    Each row names one recording under the level it was picked on and offers a box per channel
    it holds frames on: ticking one keeps that channel's frames in what plays, and the leading
    box moves every channel the recording offers at once. A channel switched off for the whole
    reconstruction shows its boxes muted while they stay as clickable as any other, so the
    reader's per-recording choice keeps standing. A click on a row shows the recording where it
    sits on disk, and the button beside it asks to take the recording out of the reconstruction
    for good. The list holds on to its last row, so one recording always stands.
    """

    def __init__(
        self,
        *,
        stems_layout: StemsListLayout,
        language_manager: LanguageManager,
        status_bar: GUIStatusBar,
        initial_collapsed: bool = False,
    ) -> None:
        self._language_manager = language_manager
        self._lbl_stems = language_manager["reconstructions.reconstruction.label.stems"]
        self._lbl_empty = language_manager["reconstructions.reconstruction.label.stems_empty"]
        self._lbl_collapse = language_manager["reconstructions.reconstruction.label.collapse_levels"]
        self._setup_template = language_manager["reconstructions.reconstruction.template.stems_setup"]
        self._mode_labels = {
            HierarchyMode.ROUND_ROBIN: language_manager["reconstructions.reconstruction.label.stems_mode_round_robin"],
            HierarchyMode.STRICT: language_manager["reconstructions.reconstruction.label.stems_mode_strict"],
        }
        self._status_bar = status_bar
        self._view_model: Optional[ReconstructionStemsViewModel] = None
        self._stems_list = GUIStemsList(
            prefix=PRE_RECONSTRUCTION_STEMS,
            layout=stems_layout,
            language_manager=language_manager,
            status_bar=status_bar,
            draggable=False,
            removable=True,
            retain_last_row=True,
            master_checkbox=True,
        )

        self.on_stem_channels_changed: Optional[Callable[[int, FrozenSet[ChannelName]], None]] = None
        self.on_stem_remove_requested: Optional[Callable[[int], None]] = None

        super().__init__(tag=TAG_RECONSTRUCTIONS_RECONSTRUCTION_PANEL_STEMS)
        self._enable_vertical_collapse(
            initial_collapsed=initial_collapsed,
            auto_height=True,
        )

    @property
    def stems_list(self) -> GUIStemsList:
        """The list the recordings are drawn in, which is what addresses their widgets."""
        return self._stems_list

    def create_panel(self, parent: str) -> None:
        with self._collapsible_card(
            parent,
            self._lbl_stems,
            glyph=self._glyphs.headers.source,
            width=0,
            no_scrollbar=True,
        ):
            dpg.add_text(
                "",
                tag=TAG_RECONSTRUCTIONS_RECONSTRUCTION_TEXT_STEMS_SETUP,
                parent=self._body_container,
                show=False,
            )
            dpg.add_text(
                self._lbl_empty,
                tag=TAG_RECONSTRUCTIONS_RECONSTRUCTION_TEXT_STEMS_EMPTY,
                parent=self._body_container,
                show=False,
            )
            self._create_collapse_toggle()
            self._stems_list.create(self._body_container, show=False)

        self._stems_list.on_channels_changed = self._on_channels_changed
        self._stems_list.on_row_activated = self._on_row_activated
        self._stems_list.on_remove_requested = self._on_remove_requested

    def update_view(self, view_model: ReconstructionStemsViewModel) -> None:
        self._view_model = view_model
        self._render_setup_line(view_model)
        dpg_configure_item(
            TAG_RECONSTRUCTIONS_RECONSTRUCTION_TEXT_STEMS_EMPTY,
            show=view_model.show_empty_state,
        )
        dpg_configure_item(
            TAG_RECONSTRUCTIONS_RECONSTRUCTION_CHECKBOX_COLLAPSE_LEVELS,
            show=view_model.stems.level_count >= MINIMUM_COLLAPSIBLE_LEVELS,
        )
        dpg_configure_item(self._stems_list.tag, show=bool(view_model.stems.rows))
        self._stems_list.update_view(self._banded(view_model.stems))

    def _create_collapse_toggle(self) -> None:
        """The reader's choice of banding: one table, or a caption per picking level."""
        checkbox = dpg.add_checkbox(
            label=self._lbl_collapse,
            tag=TAG_RECONSTRUCTIONS_RECONSTRUCTION_CHECKBOX_COLLAPSE_LEVELS,
            parent=self._body_container,
            callback=self._on_collapse_toggled,
            show=False,
        )
        FontRegistry.bind_to_item(checkbox, Font.REGULAR_SMALL)
        show_tooltip(
            checkbox,
            self._language_manager["reconstructions.reconstruction.message.collapse_levels_tooltip"],
            tag=TAG_RECONSTRUCTIONS_RECONSTRUCTION_TOOLTIP_COLLAPSE_LEVELS,
        )
        self._status_bar.bind_to_item(
            TAG_RECONSTRUCTIONS_RECONSTRUCTION_CHECKBOX_COLLAPSE_LEVELS,
            self._language_manager["reconstructions.reconstruction.message.status_collapse_levels"],
        )

    def _banded(self, stems: StemsListViewModel) -> StemsListViewModel:
        """The list as the card draws it, under the banding the reader last asked for."""
        collapsed = bool(dpg.get_value(TAG_RECONSTRUCTIONS_RECONSTRUCTION_CHECKBOX_COLLAPSE_LEVELS))
        return stems.model_copy(update={"collapse_levels": collapsed})

    def _render_setup_line(
        self,
        view_model: ReconstructionStemsViewModel,
    ) -> None:
        if view_model.show_setup_line:
            mode = "" if view_model.hierarchy_mode is None else self._mode_labels[view_model.hierarchy_mode]
            dpg_set_value(
                TAG_RECONSTRUCTIONS_RECONSTRUCTION_TEXT_STEMS_SETUP,
                self._setup_template.format(
                    mode=mode,
                    cap=view_model.channel_cap,
                ),
            )

        dpg_configure_item(
            TAG_RECONSTRUCTIONS_RECONSTRUCTION_TEXT_STEMS_SETUP,
            show=view_model.show_setup_line,
        )

    def _on_collapse_toggled(self, _sender: Sender, _value: bool) -> None:
        if self._view_model is not None:
            self._stems_list.update_view(self._banded(self._view_model.stems))

    def _on_channels_changed(self, key: str, channels: FrozenSet[ChannelName]) -> None:
        self.call(self.on_stem_channels_changed, int(key), channels)

    def _on_remove_requested(self, key: str) -> None:
        self.call(self.on_stem_remove_requested, int(key))

    def _on_row_activated(self, key: str) -> None:
        """A clicked row shows its recording where it sits on disk."""
        row = self._stems_list.row(key)
        if row is not None and row.available:
            open_path_in_explorer(row.path)
