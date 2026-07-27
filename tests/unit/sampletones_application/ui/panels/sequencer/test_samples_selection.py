from typing import Optional, Tuple

from sampletones_application.ui.panels.sequencer.samples import GUISequencerSamplesPanel
from sampletones_application.view_model.sequencer.samples import SampleEntryViewModel

ENTRIES: Tuple[SampleEntryViewModel, ...] = (
    SampleEntryViewModel(sample_id="kick-id", name="Kick", loop=False),
    SampleEntryViewModel(sample_id="bass-id", name="Bass", loop=True),
)


def _panel(
    selected_sample_id: Optional[str],
    selected_row: Optional[int],
    entries: Tuple[SampleEntryViewModel, ...] = ENTRIES,
) -> GUISequencerSamplesPanel:
    """Builds a panel without its DearPyGui-dependent constructor.

    The selection accessor reads only the cached entries and the highlighted row, so a running
    GUI context is unnecessary here.
    """
    panel = GUISequencerSamplesPanel.__new__(GUISequencerSamplesPanel)
    panel._entries = entries
    panel._selected_sample_id = selected_sample_id
    panel._selected_row = selected_row
    return panel


class TestSelectionAccessor:
    def test_reports_the_highlighted_sample(self) -> None:
        panel = _panel("bass-id", 1)

        selection = panel.selection

        assert selection is not None
        assert selection.sample_id == "bass-id"
        assert selection.position == 1
        assert selection.name == "Bass"
        assert selection.label == "01: Bass"

    def test_absent_without_a_selection(self) -> None:
        assert _panel(None, None).selection is None

    def test_absent_once_the_selected_sample_leaves_the_pool(self) -> None:
        panel = _panel("removed-id", 0)

        assert panel.selection is None

    def test_follows_a_renamed_sample(self) -> None:
        panel = _panel("kick-id", 0)
        panel._entries = (SampleEntryViewModel(sample_id="kick-id", name="Thump", loop=False),)

        selection = panel.selection

        assert selection is not None
        assert selection.label == "00: Thump"
