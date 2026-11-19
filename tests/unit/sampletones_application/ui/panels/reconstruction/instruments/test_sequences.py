from typing import Dict, Final, List, Tuple
from unittest.mock import MagicMock

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.paths import LANG_EN, PALETTES_DIRECTORY, THEME_DIRECTORY
from sampletones_application.tags.general import TAG_GLOBAL_THEME_INPUT_INVALID
from sampletones_application.ui.panels.reconstruction.instruments import sequences as sequences_module
from sampletones_application.ui.panels.reconstruction.instruments.sequences import (
    SequenceInputs,
    sequence_input_tag,
)
from sampletones_application.ui.themes.setup import setup_themes
from sampletones_application.ui.themes.theme import Theme
from sampletones_application.utils.palette.catalog import PaletteCatalog
from sampletones_application.utils.palette.source import PaletteSource
from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.features.envelope import Envelope
from sampletones_core.features.text import format_envelope

CHANNEL: Final[ChannelName] = ChannelName.PULSE1
FEATURE: Final[FeatureKey] = FeatureKey.VOLUME
VOLUME_RANGE: Final[Tuple[int, int]] = (0, 15)
FIELD: Final[str] = sequence_input_tag(CHANNEL, FEATURE)
STANDING: Final[Envelope[int]] = Envelope[int](items=(4, 8))


@pytest.fixture(autouse=True)
def registered_themes() -> None:
    """Registers the themes the inputs resolve on construction, as startup does."""
    setup_themes(THEME_DIRECTORY, PaletteSource(PaletteCatalog.load(PALETTES_DIRECTORY).default))


@pytest.fixture
def bound_themes(monkeypatch: pytest.MonkeyPatch) -> List[str]:
    tags: List[str] = []
    monkeypatch.setattr(Theme, "bind_to_item", lambda self, item: tags.append(self.tag))
    return tags


@pytest.fixture
def field_values(monkeypatch: pytest.MonkeyPatch) -> Dict[str, str]:
    """The texts written into the fields, standing in for the widgets."""
    values: Dict[str, str] = {}
    monkeypatch.setattr(sequences_module, "dpg_set_value", values.__setitem__)
    monkeypatch.setattr(dpg, "set_value", values.__setitem__)
    return values


@pytest.fixture
def typed(bound_themes: List[str], field_values: Dict[str, str]) -> List[Envelope[int]]:
    return []


@pytest.fixture
def inputs(typed: List[Envelope[int]]) -> SequenceInputs:
    sequence_inputs = SequenceInputs(copy_width=40, language_manager=LanguageManager(LANG_EN), status_bar=MagicMock())
    sequence_inputs.on_typed = lambda _channel, _feature, envelope: typed.append(envelope)
    sequence_inputs.show(CHANNEL, FEATURE, STANDING)
    return sequence_inputs


def _type(inputs: SequenceInputs, text: str) -> None:
    inputs._on_typed(FIELD, text, (CHANNEL, FEATURE, VOLUME_RANGE))


class TestATypedSequence:
    """A typed sequence is held to the values its dimension writes; text reading as none changes nothing."""

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("0 20 -3 15", Envelope[int](items=(0, 15, 0, 15))),
            ("15 | 99 8", Envelope[int](items=(15, 15, 8), loop_point=1)),
            ("  7   7 ", Envelope[int](items=(7, 7))),
            ("", Envelope[int]()),
        ],
        ids=["beyond-both-ends", "loop-point-kept", "loose-spacing", "empty"],
    )
    def test_the_sequence_taken_is_the_clamped_one(
        self,
        inputs: SequenceInputs,
        typed: List[Envelope[int]],
        field_values: Dict[str, str],
        text: str,
        expected: Envelope[int],
    ) -> None:
        _type(inputs, text)

        assert typed == [expected]
        assert inputs.standing(CHANNEL, FEATURE) == expected
        assert field_values[FIELD] == format_envelope(expected)

    @pytest.mark.parametrize("text", ["4 x 8", "4 | 8 | 2", "4 8 |", "4.5", "| |"])
    def test_text_reading_as_no_sequence_marks_the_field_and_changes_nothing(
        self,
        inputs: SequenceInputs,
        typed: List[Envelope[int]],
        bound_themes: List[str],
        field_values: Dict[str, str],
        text: str,
    ) -> None:
        _type(inputs, text)

        assert typed == []
        assert inputs.standing(CHANNEL, FEATURE) == STANDING
        assert bound_themes[-1] == TAG_GLOBAL_THEME_INPUT_INVALID
        assert FIELD not in field_values

    def test_a_dimension_never_shown_starts_from_nothing(self, inputs: SequenceInputs) -> None:
        assert inputs.standing(ChannelName.NOISE, FEATURE) == Envelope[int]()

    def test_each_channel_holds_its_own_typed_sequence(self, inputs: SequenceInputs) -> None:
        inputs._on_typed(
            sequence_input_tag(ChannelName.TRIANGLE, FEATURE), "1 2", (ChannelName.TRIANGLE, FEATURE, (0, 1))
        )

        assert (inputs.standing(CHANNEL, FEATURE), inputs.standing(ChannelName.TRIANGLE, FEATURE)) == (
            STANDING,
            Envelope[int](items=(1, 1)),
        )
