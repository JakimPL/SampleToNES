from types import SimpleNamespace
from typing import Any, Dict, List, Tuple

import pytest

from sampletones_application.ui.panels.sequencer.tracker import themes as themes_module
from sampletones_application.ui.panels.sequencer.tracker.callbacks import ThemeKey
from sampletones_application.ui.panels.sequencer.tracker.themes import TrackerThemes
from sampletones_application.utils.palette.colors.base import BaseColor
from sampletones_application.utils.palette.colors.written import LiteralColor
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_application.view_model.sequencer.voices import VoiceKind

MUTED_TEXT_FRACTION = 0.25

TEXT_COLORS = SimpleNamespace(
    voice=LiteralColor((118, 122, 142, 255)),
    sample=LiteralColor((224, 200, 96, 255)),
    instrument=LiteralColor((255, 112, 223, 255)),
    transpose=LiteralColor((192, 192, 192, 255)),
    volume=LiteralColor((100, 220, 100, 255)),
    row=LiteralColor((90, 90, 90, 255)),
)

LAYOUT = SimpleNamespace(
    colors=SimpleNamespace(text=TEXT_COLORS),
    tracker=SimpleNamespace(muted_text_fraction=MUTED_TEXT_FRACTION),
)


class TestWhichThemesAreBuilt:
    """Every shade a cell can wear is built once, each kind in its own color and each with a twin."""

    @staticmethod
    def _built(monkeypatch: pytest.MonkeyPatch) -> Tuple[Dict[ThemeKey, int], Dict[ThemeKey, int], List[BaseColor]]:
        colors: List[BaseColor] = []

        def _record(color: BaseColor, *_arguments: Any) -> int:
            colors.append(color)
            return len(colors)

        monkeypatch.setattr(themes_module, "create_selectable_text_theme", _record)
        themes = TrackerThemes(LAYOUT)
        themes._create_subcolumn_themes()
        return themes._subcolumn, themes._muted_subcolumn, colors

    def test_the_voice_slot_is_built_in_a_color_for_each_kind(self, monkeypatch: pytest.MonkeyPatch) -> None:
        subcolumn, _, _ = self._built(monkeypatch)

        voice_themes = {theme_key for theme_key in subcolumn if theme_key[0] is SubColumn.VOICE}

        assert voice_themes == {
            (SubColumn.VOICE, None),
            (SubColumn.VOICE, VoiceKind.SAMPLE),
            (SubColumn.VOICE, VoiceKind.INSTRUMENT),
        }

    def test_each_kind_is_built_in_its_own_color(self, monkeypatch: pytest.MonkeyPatch) -> None:
        subcolumn, _, colors = self._built(monkeypatch)

        sample = colors[subcolumn[(SubColumn.VOICE, VoiceKind.SAMPLE)] - 1]
        instrument = colors[subcolumn[(SubColumn.VOICE, VoiceKind.INSTRUMENT)] - 1]

        assert (sample.rgba, instrument.rgba) == (TEXT_COLORS.sample.rgba, TEXT_COLORS.instrument.rgba)

    def test_every_theme_has_a_dimmed_twin(self, monkeypatch: pytest.MonkeyPatch) -> None:
        subcolumn, muted_subcolumn, _ = self._built(monkeypatch)

        assert set(muted_subcolumn) == set(subcolumn)


class TestWhichThemeACellWears:
    """A cell reads its shade from the slot it stands in and whether its channel is silenced."""

    @staticmethod
    def _themes() -> TrackerThemes:
        themes = TrackerThemes.__new__(TrackerThemes)
        themes._subcolumn = {(SubColumn.VOICE, VoiceKind.SAMPLE): 11, (SubColumn.TRANSPOSE, None): 13}
        themes._muted_subcolumn = {(SubColumn.VOICE, VoiceKind.SAMPLE): 111, (SubColumn.TRANSPOSE, None): 113}
        themes._header = 20
        themes._muted_header = 120
        return themes

    def test_an_audible_cell_takes_the_full_shade(self) -> None:
        assert self._themes().cell(SubColumn.VOICE, VoiceKind.SAMPLE, muted=False) == 11

    def test_a_silenced_cell_takes_the_dimmed_twin(self) -> None:
        assert self._themes().cell(SubColumn.VOICE, VoiceKind.SAMPLE, muted=True) == 111

    def test_an_audible_header_takes_the_full_shade(self) -> None:
        assert self._themes().header(muted=False) == 20

    def test_a_silenced_header_takes_the_dimmed_twin(self) -> None:
        assert self._themes().header(muted=True) == 120
