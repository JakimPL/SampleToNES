import pytest

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.loader import load_layout_config
from sampletones_application.layout.sequencer import SequencerLayout
from sampletones_application.paths import BEHAVIOR_DIRECTORY, LANG_EN, LAYOUT_DIRECTORY
from sampletones_application.ui.panels.sequencer.history import GUISequencerHistoryPanel
from sampletones_application.view_model.sequencer.history import (
    HistoryEntryViewModel,
    HistoryViewModel,
)


@pytest.fixture
def sequencer_layout() -> SequencerLayout:
    return load_layout_config(LAYOUT_DIRECTORY, BEHAVIOR_DIRECTORY).sequencer


@pytest.fixture
def panel(sequencer_layout: SequencerLayout) -> GUISequencerHistoryPanel:
    return GUISequencerHistoryPanel(
        layout=sequencer_layout,
        language_manager=LanguageManager(LANG_EN),
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
