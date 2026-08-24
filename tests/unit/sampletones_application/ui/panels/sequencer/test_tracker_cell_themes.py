from types import SimpleNamespace
from typing import Any, Dict, FrozenSet, List, Optional, Tuple

import pytest

from sampletones_application.ui.elements.table.cells import EditableCells
from sampletones_application.ui.panels.sequencer import tracker as tracker_module
from sampletones_application.ui.panels.sequencer.display import CellKey, CellKinds
from sampletones_application.ui.panels.sequencer.tracker import GUISequencerTrackerPanel, ThemeKey
from sampletones_application.utils.palette.colors.base import BaseColor
from sampletones_application.utils.palette.colors.written import LiteralColor
from sampletones_application.view_model.sequencer.channels import (
    SequencerChannelsViewModel,
)
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_application.view_model.sequencer.tracker import (
    SequencerCellViewModel,
    SequencerRowViewModel,
    SequencerTrackerViewModel,
)
from sampletones_application.view_model.sequencer.voices import VoiceKind
from sampletones_core.constants.enums import ChannelName
from sampletones_core.utils.display import display_id, display_transpose, display_volume
from sampletones_shared.types.application import Sender

ROW_COUNT = 2
MUTED_TEXT_FRACTION = 0.25

THEME_IDS: Dict[ThemeKey, int] = {
    (SubColumn.VOICE, None): 10,
    (SubColumn.VOICE, VoiceKind.SAMPLE): 11,
    (SubColumn.VOICE, VoiceKind.INSTRUMENT): 12,
    (SubColumn.TRANSPOSE, None): 13,
    (SubColumn.VOLUME, None): 14,
}
MUTED_THEME_IDS: Dict[ThemeKey, int] = {theme_key: theme + 100 for theme_key, theme in THEME_IDS.items()}

TEXT_COLORS = SimpleNamespace(
    voice=LiteralColor((118, 122, 142, 255)),
    sample=LiteralColor((224, 200, 96, 255)),
    instrument=LiteralColor((255, 112, 223, 255)),
    transpose=LiteralColor((192, 192, 192, 255)),
    volume=LiteralColor((100, 220, 100, 255)),
)


def _cell_widget(key: CellKey) -> int:
    """A stable stand-in widget id per cell."""
    row_index, channel, subcolumn = key
    column = 0 if channel is None else ChannelName.items().index(channel) + 1
    return 1000 + 100 * column + 10 * row_index + list(SubColumn).index(subcolumn)


def _keys() -> List[CellKey]:
    return [
        (row_index, channel, subcolumn)
        for row_index in range(ROW_COUNT)
        for channel in (None, *ChannelName.items())
        for subcolumn in SubColumn
    ]


def _panel(
    *,
    cell_kinds: Optional[CellKinds] = None,
    muted: FrozenSet[ChannelName] = frozenset(),
) -> GUISequencerTrackerPanel:
    """Builds a panel around the state a cell's theme is read from, with no DearPyGui context."""
    panel = GUISequencerTrackerPanel.__new__(GUISequencerTrackerPanel)
    panel._layout = SimpleNamespace(
        colors=SimpleNamespace(text=TEXT_COLORS),
        tracker=SimpleNamespace(muted_text_fraction=MUTED_TEXT_FRACTION),
    )
    panel._cell_kinds = dict(cell_kinds or {})
    panel._subcolumn_themes = dict(THEME_IDS)
    panel._muted_subcolumn_themes = dict(MUTED_THEME_IDS)
    panel._current_channels = SequencerChannelsViewModel(muted=muted)
    panel._current_row_count = ROW_COUNT
    panel._editable_cells = EditableCells()
    for key in _keys():
        panel._editable_cells.register(key, _cell_widget(key))

    return panel


@pytest.fixture
def bound(monkeypatch: pytest.MonkeyPatch) -> Dict[Sender, int]:
    """The theme each widget was last bound to."""
    themes: Dict[Sender, int] = {}
    monkeypatch.setattr(tracker_module.dpg, "bind_item_theme", themes.__setitem__)
    return themes


def _view_model(rows: Tuple[SequencerRowViewModel, ...]) -> SequencerTrackerViewModel:
    return SequencerTrackerViewModel(frame_index=0, frame_count=1, rows=rows)


def _row(
    index: int,
    *,
    named: Optional[Tuple[ChannelName, VoiceKind]] = None,
) -> SequencerRowViewModel:
    """A row whose channels stand empty, save one naming a voice of the given kind."""
    cells = {
        channel: SequencerCellViewModel(
            voice=display_id(None),
            transpose=display_transpose(None),
            volume=display_volume(None),
            kind=None,
        )
        for channel in ChannelName.items()
    }
    sample_channels: FrozenSet[ChannelName] = frozenset()
    if named is not None:
        channel, kind = named
        cells[channel] = SequencerCellViewModel(
            voice=display_id(0),
            transpose=display_transpose(None),
            volume=display_volume(None),
            kind=kind,
        )
        if kind is VoiceKind.SAMPLE:
            sample_channels = frozenset({channel})

    return SequencerRowViewModel(index=index, cells=cells, sample_channels=sample_channels)


class TestWhatColourAVoiceSlotWears:
    """The slot takes the colour of the kind standing in it, so the grid reports what it holds."""

    def test_a_slot_naming_nothing_takes_the_neutral_shade(self) -> None:
        panel = _panel()

        theme = panel._cell_theme((0, ChannelName.PULSE1, SubColumn.VOICE))

        assert theme == THEME_IDS[(SubColumn.VOICE, None)]

    @pytest.mark.parametrize(
        "kind",
        [VoiceKind.SAMPLE, VoiceKind.INSTRUMENT],
        ids=lambda kind: kind.value,
    )
    def test_a_slot_naming_a_voice_takes_that_kinds_colour(self, kind: VoiceKind) -> None:
        key = (0, ChannelName.PULSE1, SubColumn.VOICE)
        panel = _panel(cell_kinds={key: kind})

        assert panel._cell_theme(key) == THEME_IDS[(SubColumn.VOICE, kind)]

    def test_the_sample_column_takes_the_kind_its_own_slot_names(self) -> None:
        key = (0, None, SubColumn.VOICE)
        panel = _panel(cell_kinds={key: VoiceKind.SAMPLE})

        assert panel._cell_theme(key) == THEME_IDS[(SubColumn.VOICE, VoiceKind.SAMPLE)]

    @pytest.mark.parametrize(
        "subcolumn",
        [SubColumn.TRANSPOSE, SubColumn.VOLUME],
        ids=lambda subcolumn: subcolumn.value,
    )
    def test_the_other_slots_keep_their_own_colour(self, subcolumn: SubColumn) -> None:
        """A pitch and a volume mean the same whatever voice sounds them."""
        panel = _panel(cell_kinds={(0, ChannelName.PULSE1, SubColumn.VOICE): VoiceKind.INSTRUMENT})

        theme = panel._cell_theme((0, ChannelName.PULSE1, subcolumn))

        assert theme == THEME_IDS[(subcolumn, None)]

    def test_a_silenced_channel_dims_the_kind_it_names(self) -> None:
        key = (0, ChannelName.TRIANGLE, SubColumn.VOICE)
        panel = _panel(
            cell_kinds={key: VoiceKind.INSTRUMENT},
            muted=frozenset({ChannelName.TRIANGLE}),
        )

        assert panel._cell_theme(key) == MUTED_THEME_IDS[(SubColumn.VOICE, VoiceKind.INSTRUMENT)]

    def test_the_sample_column_is_never_silenced(self) -> None:
        """It speaks for every channel, so no one channel's mute reaches it."""
        key = (0, None, SubColumn.VOICE)
        panel = _panel(
            cell_kinds={key: VoiceKind.SAMPLE},
            muted=frozenset(ChannelName.items()),
        )

        assert panel._cell_theme(key) == THEME_IDS[(SubColumn.VOICE, VoiceKind.SAMPLE)]


class TestWhichKindsTheGridReads:
    def test_every_voice_slot_is_covered(self) -> None:
        panel = _panel()

        cell_kinds = panel._compute_cell_kinds(_view_model((_row(0), _row(1))))

        assert set(cell_kinds) == {key for key in _keys() if key[2] is SubColumn.VOICE}

    def test_a_named_channel_reports_its_voices_kind(self) -> None:
        panel = _panel()

        cell_kinds = panel._compute_cell_kinds(
            _view_model((_row(0, named=(ChannelName.PULSE2, VoiceKind.INSTRUMENT)),)),
        )

        assert cell_kinds[(0, ChannelName.PULSE2, SubColumn.VOICE)] is VoiceKind.INSTRUMENT

    def test_the_sample_column_reports_the_rows_own_kind(self) -> None:
        panel = _panel()

        cell_kinds = panel._compute_cell_kinds(
            _view_model((_row(0, named=(ChannelName.PULSE1, VoiceKind.SAMPLE)),)),
        )

        assert cell_kinds[(0, None, SubColumn.VOICE)] is VoiceKind.SAMPLE

    def test_an_instrument_leaves_the_sample_column_stating_nothing(self) -> None:
        panel = _panel()

        cell_kinds = panel._compute_cell_kinds(
            _view_model((_row(0, named=(ChannelName.PULSE1, VoiceKind.INSTRUMENT)),)),
        )

        assert cell_kinds[(0, None, SubColumn.VOICE)] is None


class TestWhatARefreshRebinds:
    """A refresh re-themes the slots an edit changed, which is what keeps its cost with the edit."""

    def test_a_changed_kind_rebinds_its_cell(self, bound: Dict[Sender, int]) -> None:
        key = (0, ChannelName.PULSE1, SubColumn.VOICE)
        panel = _panel()

        panel._reconcile_cell_kinds({key: VoiceKind.SAMPLE})

        assert bound[_cell_widget(key)] == THEME_IDS[(SubColumn.VOICE, VoiceKind.SAMPLE)]
        assert panel._cell_kinds[key] is VoiceKind.SAMPLE

    def test_an_unchanged_kind_leaves_its_cell_alone(self, bound: Dict[Sender, int]) -> None:
        key = (0, ChannelName.PULSE1, SubColumn.VOICE)
        panel = _panel(cell_kinds={key: VoiceKind.SAMPLE})

        panel._reconcile_cell_kinds({key: VoiceKind.SAMPLE})

        assert not bound

    def test_only_the_changed_cells_are_rebound(self, bound: Dict[Sender, int]) -> None:
        moved = (0, ChannelName.PULSE1, SubColumn.VOICE)
        standing = (1, ChannelName.NOISE, SubColumn.VOICE)
        panel = _panel(cell_kinds={moved: VoiceKind.SAMPLE, standing: VoiceKind.SAMPLE})

        panel._reconcile_cell_kinds({moved: VoiceKind.INSTRUMENT, standing: VoiceKind.SAMPLE})

        assert set(bound) == {_cell_widget(moved)}

    def test_a_voice_taken_out_returns_its_cell_to_the_neutral_shade(self, bound: Dict[Sender, int]) -> None:
        key = (0, ChannelName.PULSE1, SubColumn.VOICE)
        panel = _panel(cell_kinds={key: VoiceKind.SAMPLE})

        panel._reconcile_cell_kinds({key: None})

        assert bound[_cell_widget(key)] == THEME_IDS[(SubColumn.VOICE, None)]


class TestWhatAnEditShowsAtOnce:
    """The number and the colour are written together, so a typed voice reads whole in one frame."""

    def test_a_placed_voice_takes_its_colour_with_its_number(self, bound: Dict[Sender, int]) -> None:
        panel = _panel()
        key = (0, ChannelName.PULSE1, SubColumn.VOICE)

        panel._show_voice(0, ChannelName.PULSE1, display_id(3), VoiceKind.INSTRUMENT)

        assert panel._editable_cells.values[key] == display_id(3)
        assert bound[_cell_widget(key)] == THEME_IDS[(SubColumn.VOICE, VoiceKind.INSTRUMENT)]

    def test_a_cleared_slot_drops_its_number_and_its_colour(self, bound: Dict[Sender, int]) -> None:
        key = (0, ChannelName.PULSE1, SubColumn.VOICE)
        panel = _panel(cell_kinds={key: VoiceKind.SAMPLE})
        panel._editable_cells.values[key] = display_id(3)

        panel._forget_voice(0, ChannelName.PULSE1)

        assert key not in panel._editable_cells.values
        assert bound[_cell_widget(key)] == THEME_IDS[(SubColumn.VOICE, None)]


class TestWhichThemesAreBuilt:
    @staticmethod
    def _built(monkeypatch: pytest.MonkeyPatch) -> Tuple[GUISequencerTrackerPanel, List[BaseColor]]:
        colors: List[BaseColor] = []

        def _record(color: BaseColor, *_arguments: Any) -> int:
            colors.append(color)
            return len(colors)

        monkeypatch.setattr(tracker_module, "create_selectable_text_theme", _record)
        panel = _panel()
        panel._subcolumn_themes = {}
        panel._muted_subcolumn_themes = {}
        panel._create_subcolumn_themes()
        return panel, colors

    def test_the_voice_slot_is_built_in_a_colour_for_each_kind(self, monkeypatch: pytest.MonkeyPatch) -> None:
        panel, _ = self._built(monkeypatch)

        voice_themes = {theme_key for theme_key in panel._subcolumn_themes if theme_key[0] is SubColumn.VOICE}

        assert voice_themes == {
            (SubColumn.VOICE, None),
            (SubColumn.VOICE, VoiceKind.SAMPLE),
            (SubColumn.VOICE, VoiceKind.INSTRUMENT),
        }

    def test_each_kind_is_built_in_its_own_colour(self, monkeypatch: pytest.MonkeyPatch) -> None:
        panel, colors = self._built(monkeypatch)

        sample = colors[panel._subcolumn_themes[(SubColumn.VOICE, VoiceKind.SAMPLE)] - 1]
        instrument = colors[panel._subcolumn_themes[(SubColumn.VOICE, VoiceKind.INSTRUMENT)] - 1]

        assert (sample.rgba, instrument.rgba) == (TEXT_COLORS.sample.rgba, TEXT_COLORS.instrument.rgba)

    def test_every_theme_has_a_dimmed_twin(self, monkeypatch: pytest.MonkeyPatch) -> None:
        panel, _ = self._built(monkeypatch)

        assert set(panel._muted_subcolumn_themes) == set(panel._subcolumn_themes)
