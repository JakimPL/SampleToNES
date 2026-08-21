from typing import Any, Callable, FrozenSet, List, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.categories.context import channel_label
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import SUF_CHANNELS, SUF_GROUP
from sampletones_application.tags.reconstructions import (
    PRE_RECONSTRUCTION_STEM,
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_GROUP_STEMS,
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_PANEL_STEMS,
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_TEXT_STEMS_EMPTY,
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_TEXT_STEMS_SETUP,
)
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.utils.gui.dpg import dpg_delete_item
from sampletones_application.view_model.reconstruction.stems import (
    ReconstructionStemsViewModel,
    StemViewModel,
)
from sampletones_core.constants.enums import HierarchyMode
from sampletones_shared.types.application import Sender


class GUIReconstructionStemsPanel(GUIPanel):
    """The stems of the loaded reconstruction, one checkbox row per stem.

    A checked stem keeps its frames in what plays; unchecking silences them across the
    waveform, playback, and WAV export. Rows mirror the channel checkboxes: a stem with
    no assigned frames is shown disabled, a single-source reconstruction shows one row
    the same way, and a loaded reconstruction recording no source shows the empty state.
    """

    def __init__(
        self,
        *,
        language_manager: LanguageManager,
        initial_collapsed: bool = False,
    ) -> None:
        self._language_manager = language_manager
        self._lbl_stems = language_manager["reconstructions.reconstruction.label.stems"]
        self._lbl_empty = language_manager["reconstructions.reconstruction.label.stems_empty"]
        self._setup_template = language_manager["reconstructions.reconstruction.template.stems_setup"]
        self._mode_labels = {
            HierarchyMode.ROUND_ROBIN: language_manager["reconstructions.reconstruction.label.stems_mode_round_robin"],
            HierarchyMode.STRICT: language_manager["reconstructions.reconstruction.label.stems_mode_strict"],
        }
        self._stem_rows: List[Tuple[int, str]] = []

        self.on_stems_changed: Optional[Callable[[FrozenSet[int]], None]] = None

        super().__init__(tag=TAG_RECONSTRUCTIONS_RECONSTRUCTION_PANEL_STEMS)
        self._enable_vertical_collapse(
            initial_collapsed=initial_collapsed,
            auto_height=True,
        )

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
            dpg.add_group(
                tag=TAG_RECONSTRUCTIONS_RECONSTRUCTION_GROUP_STEMS,
                parent=self._body_container,
            )

    def update_view(self, view_model: ReconstructionStemsViewModel) -> None:
        self._sync_rows(view_model.stems)
        self._render_setup_line(view_model)
        dpg.configure_item(
            TAG_RECONSTRUCTIONS_RECONSTRUCTION_TEXT_STEMS_EMPTY,
            show=view_model.show_empty_state,
        )
        for row in view_model.stems:
            self._render_row(row)

    def _render_setup_line(
        self,
        view_model: ReconstructionStemsViewModel,
    ) -> None:
        if view_model.show_setup_line:
            mode = "" if view_model.hierarchy_mode is None else self._mode_labels[view_model.hierarchy_mode]
            dpg.set_value(
                TAG_RECONSTRUCTIONS_RECONSTRUCTION_TEXT_STEMS_SETUP,
                self._setup_template.format(
                    mode=mode,
                    cap=view_model.channel_cap,
                ),
            )

        dpg.configure_item(
            TAG_RECONSTRUCTIONS_RECONSTRUCTION_TEXT_STEMS_SETUP,
            show=view_model.show_setup_line,
        )

    def _sync_rows(self, rows: Tuple[StemViewModel, ...]) -> None:
        """Rebuilds the checkbox rows when the stem set changes, keeps them otherwise."""
        expected_ids = [row.stem_id for row in rows]
        current_ids = [stem_id for stem_id, _tag in self._stem_rows]
        if current_ids != expected_ids:
            for _stem_id, tag in self._stem_rows:
                dpg_delete_item(tag)

            self._stem_rows = [(row.stem_id, self._create_stem_row(row)) for row in rows]

    def _create_stem_row(self, row: StemViewModel) -> str:
        group_tag = self._stem_group_tag(row.stem_id)
        checkbox_tag = self._stem_checkbox_tag(row.stem_id)
        with dpg.group(
            horizontal=True,
            tag=group_tag,
            parent=TAG_RECONSTRUCTIONS_RECONSTRUCTION_GROUP_STEMS,
        ):
            dpg.add_checkbox(
                label=row.label,
                tag=checkbox_tag,
                callback=self._on_stem_changed,
            )
            dpg.add_text(
                self._channels_text(row),
                tag=self._stem_channels_tag(row.stem_id),
            )

        FontRegistry.bind_to_item(checkbox_tag, Font.REGULAR_SMALL)
        return group_tag

    def _render_row(self, row: StemViewModel) -> None:
        checkbox_tag = self._stem_checkbox_tag(row.stem_id)
        dpg.configure_item(checkbox_tag, label=row.label)
        dpg.configure_item(checkbox_tag, enabled=row.enabled)
        dpg.set_value(checkbox_tag, row.selected)
        dpg.set_value(
            self._stem_channels_tag(row.stem_id),
            self._channels_text(row),
        )

    def _on_stem_changed(self, _sender: Sender, _app_data: Any) -> None:
        selected = frozenset(
            stem_id for stem_id, _tag in self._stem_rows if dpg.get_value(self._stem_checkbox_tag(stem_id))
        )
        self.call(self.on_stems_changed, selected)

    def _channels_text(self, row: StemViewModel) -> str:
        return ", ".join(channel_label(self._language_manager, channel) for channel in row.channels)

    @staticmethod
    def _stem_checkbox_tag(stem_id: int) -> str:
        return compose_tag(PRE_RECONSTRUCTION_STEM, str(stem_id))

    @staticmethod
    def _stem_group_tag(stem_id: int) -> str:
        return compose_tag(
            PRE_RECONSTRUCTION_STEM,
            str(stem_id),
            SUF_GROUP,
        )

    @staticmethod
    def _stem_channels_tag(stem_id: int) -> str:
        return compose_tag(
            PRE_RECONSTRUCTION_STEM,
            str(stem_id),
            SUF_CHANNELS,
        )
