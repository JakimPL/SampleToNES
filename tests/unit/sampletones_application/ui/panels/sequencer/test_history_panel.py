from unittest.mock import MagicMock

import pytest

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.config import LayoutConfig
from sampletones_application.layout.loader import load_layout_config
from sampletones_application.layout.tabs.sequencer import SequencerLayout
from sampletones_application.paths import (
    BEHAVIOR_DIRECTORY,
    LANG_EN,
    LAYOUT_DIRECTORY,
    PALETTES_DIRECTORY,
)
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.panels.sequencer.history import GUISequencerHistoryPanel
from sampletones_application.utils.palette.catalog import PaletteCatalog
from sampletones_application.utils.palette.source import PaletteSource
from sampletones_application.view_model.sequencer.history import (
    HistoryEntryViewModel,
    HistoryViewModel,
)


@pytest.fixture
def layout_config() -> LayoutConfig:
    source = PaletteSource(PaletteCatalog.load(PALETTES_DIRECTORY).default)
    return load_layout_config(LAYOUT_DIRECTORY, BEHAVIOR_DIRECTORY, source)


@pytest.fixture
def sequencer_layout(layout_config: LayoutConfig) -> SequencerLayout:
    return layout_config.tabs.sequencer


@pytest.fixture(autouse=True)
def configure_panel_class(layout_config: LayoutConfig) -> None:
    """Binds the glyph, section-header, and collapse geometry the panel class reads on construction.

    The application performs this once at startup; mirroring it here lets a panel built in this module
    stand on its own configuration rather than whatever an earlier test left on the shared class.
    """
    GUIPanel.configure_section_header(
        layout_config.glyphs,
        layout_config.general.section_header,
        layout_config.general.collapse,
    )


@pytest.fixture
def panel(layout_config: LayoutConfig) -> GUISequencerHistoryPanel:
    return GUISequencerHistoryPanel(
        layout=layout_config.tabs.sequencer,
        feature_colors=layout_config.general.colors.features,
        language_manager=LanguageManager(LANG_EN),
        status_bar=MagicMock(),
    )


def _view_model(count: int, cursor: int) -> HistoryViewModel:
    entries = tuple(
        HistoryEntryViewModel(
            index=index,
            label=f"entry {index}",
            detail_segments=(),
            is_current=index == cursor,
            is_future=index > cursor,
        )
        for index in range(count)
    )
    return HistoryViewModel(entries=entries, cursor=cursor)


class TestRenderWindow:
    def test_history_within_the_cap_renders_fully(
        self,
        panel: GUISequencerHistoryPanel,
        sequencer_layout: SequencerLayout,
    ) -> None:
        limit = sequencer_layout.history.max_rendered_entries
        view_model = _view_model(limit, cursor=limit // 2)

        window = panel._window(view_model)

        assert [entry.index for entry in window] == list(range(limit))

    def test_window_centers_on_the_cursor(
        self,
        panel: GUISequencerHistoryPanel,
        sequencer_layout: SequencerLayout,
    ) -> None:
        limit = sequencer_layout.history.max_rendered_entries
        cursor = limit * 2
        view_model = _view_model(limit * 4, cursor=cursor)

        window = panel._window(view_model)

        indices = [entry.index for entry in window]
        assert len(indices) == limit
        assert indices[0] == cursor - limit // 2
        assert cursor in indices

    def test_window_clamps_at_the_start(
        self,
        panel: GUISequencerHistoryPanel,
        sequencer_layout: SequencerLayout,
    ) -> None:
        limit = sequencer_layout.history.max_rendered_entries
        view_model = _view_model(limit * 4, cursor=0)

        window = panel._window(view_model)

        indices = [entry.index for entry in window]
        assert indices == list(range(limit))

    def test_window_clamps_at_the_end(
        self,
        panel: GUISequencerHistoryPanel,
        sequencer_layout: SequencerLayout,
    ) -> None:
        limit = sequencer_layout.history.max_rendered_entries
        total = limit * 4
        view_model = _view_model(total, cursor=total - 1)

        window = panel._window(view_model)

        indices = [entry.index for entry in window]
        assert indices == list(range(total - limit, total))
