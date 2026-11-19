from dataclasses import dataclass
from typing import Dict, Final, FrozenSet, List, Tuple
from unittest.mock import MagicMock

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.paths import LANG_EN, PALETTES_DIRECTORY, THEME_DIRECTORY
from sampletones_application.tags.general import (
    TAG_GLOBAL_THEME_DEFAULT,
    TAG_GLOBAL_THEME_INPUT_INVALID,
    TAG_GLOBAL_THEME_INPUT_WARNING,
)
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
from sampletones_core.exports.ceilings import FORMAT_STORED_LENGTHS
from sampletones_core.exports.format import ExportFormat
from sampletones_core.features.envelope import Envelope
from sampletones_core.features.text import format_envelope
from sampletones_core.formats.famitracker.specification.sequences import MAX_SEQUENCE_ITEMS
from sampletones_shared.constants.general import HEXADECIMAL_BASE
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

CHANNEL: Final[ChannelName] = ChannelName.PULSE1
FEATURE: Final[FeatureKey] = FeatureKey.VOLUME
VOLUME_RANGE: Final[Tuple[int, int]] = (0, 15)
FIELD: Final[str] = sequence_input_tag(CHANNEL, FEATURE)
STANDING: Final[Envelope[int]] = Envelope[int](items=(4, 8))
COPY_WIDTH: Final[int] = 40
LANGUAGE_MANAGER: Final[LanguageManager] = LanguageManager(LANG_EN)
SEQUENCE_STATUS_KEY: Final[str] = "reconstructions.instruments.message.status_sequence"
KEPT_KEYS: Final[Dict[ExportFormat, str]] = {
    ExportFormat.FAMITRACKER: "reconstructions.instruments.template.kept_famitracker",
    ExportFormat.BITPHASE: "reconstructions.instruments.template.kept_bitphase",
    ExportFormat.BITPHASE_PRESET: "reconstructions.instruments.template.kept_bitphase_preset",
}
PAST_A_SEQUENCE: Final[int] = 300
PAST_A_MACRO: Final[int] = 600


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
def blank_inputs(bound_themes: List[str], field_values: Dict[str, str]) -> SequenceInputs:
    """Inputs showing no dimension yet, as a tab stands once it is built."""
    return SequenceInputs(copy_width=COPY_WIDTH, language_manager=LANGUAGE_MANAGER, status_bar=MagicMock())


@pytest.fixture
def inputs(typed: List[Envelope[int]]) -> SequenceInputs:
    sequence_inputs = SequenceInputs(copy_width=COPY_WIDTH, language_manager=LANGUAGE_MANAGER, status_bar=MagicMock())
    sequence_inputs.on_typed = lambda _channel, _feature, envelope: typed.append(envelope)
    sequence_inputs.show(CHANNEL, FEATURE, STANDING)
    return sequence_inputs


def sequence(item_count: int) -> Envelope[int]:
    """A dimension of a given length, which is all the length warning reads of it."""
    return Envelope[int](items=(0,) * item_count)


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


class TestSequenceLengthWarning:
    @pytest.mark.parametrize(
        "item_count",
        [0, 1, MAX_SEQUENCE_ITEMS],
        ids=["empty", "single", "at_the_limit"],
    )
    def test_a_sequence_within_the_limit_keeps_the_default_theme(
        self,
        blank_inputs: SequenceInputs,
        bound_themes: List[str],
        item_count: int,
    ) -> None:
        blank_inputs.show(ChannelName.PULSE1, FeatureKey.VOLUME, sequence(item_count))
        assert bound_themes == [TAG_GLOBAL_THEME_DEFAULT]

    def test_a_sequence_beyond_the_limit_takes_the_warning_theme(
        self,
        blank_inputs: SequenceInputs,
        bound_themes: List[str],
    ) -> None:
        blank_inputs.show(ChannelName.PULSE1, FeatureKey.VOLUME, sequence(MAX_SEQUENCE_ITEMS + 1))
        assert bound_themes == [TAG_GLOBAL_THEME_INPUT_WARNING]

    def test_a_shortened_sequence_returns_to_the_default_theme(
        self,
        blank_inputs: SequenceInputs,
        bound_themes: List[str],
    ) -> None:
        blank_inputs.show(ChannelName.NOISE, FeatureKey.VOLUME, sequence(MAX_SEQUENCE_ITEMS + 40))
        blank_inputs.show(ChannelName.NOISE, FeatureKey.VOLUME, sequence(MAX_SEQUENCE_ITEMS))
        assert bound_themes == [
            TAG_GLOBAL_THEME_INPUT_WARNING,
            TAG_GLOBAL_THEME_DEFAULT,
        ]

    def test_each_dimension_carries_its_own_length(
        self,
        blank_inputs: SequenceInputs,
        bound_themes: List[str],
    ) -> None:
        blank_inputs.show(ChannelName.PULSE1, FeatureKey.VOLUME, sequence(MAX_SEQUENCE_ITEMS + 1))
        blank_inputs.show(ChannelName.PULSE1, FeatureKey.ARPEGGIO, sequence(8))
        assert bound_themes == [
            TAG_GLOBAL_THEME_INPUT_WARNING,
            TAG_GLOBAL_THEME_DEFAULT,
        ]


class TestCopyingASequence:
    def test_the_copy_button_hands_over_the_dimension_the_input_shows(
        self,
        blank_inputs: SequenceInputs,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The button is built while every dimension is still empty, so the press reads the input."""
        copied: List[str] = []
        monkeypatch.setattr(SequenceInputs, "_copy", lambda _self, text, _tag: copied.append(text))
        callback = blank_inputs.copy_callback(ChannelName.PULSE1, FeatureKey.VOLUME, "button")
        blank_inputs.show(
            ChannelName.PULSE1,
            FeatureKey.VOLUME,
            Envelope[int](items=(15, 12, 8), loop_point=1),
        )

        callback()

        assert copied == ["15 | 12 8"]

    def test_the_handler_is_one_the_framework_can_dispatch(
        self,
        blank_inputs: SequenceInputs,
    ) -> None:
        """DearPyGui reads a callback's ``__code__`` to decide how many arguments to pass it."""
        callback = blank_inputs.copy_callback(ChannelName.PULSE1, FeatureKey.VOLUME, "button")

        assert callback.__code__.co_argcount == 0


class TestSequenceStatusMessage:
    def test_a_sequence_within_the_limit_describes_editing(
        self,
        blank_inputs: SequenceInputs,
        bound_themes: List[str],
    ) -> None:
        blank_inputs.show(
            ChannelName.PULSE1,
            FeatureKey.VOLUME,
            sequence(HEXADECIMAL_BASE),
        )
        message = blank_inputs.status_message(
            ChannelName.PULSE1,
            FeatureKey.VOLUME,
        )
        assert message == LANGUAGE_MANAGER[SEQUENCE_STATUS_KEY].format(instrument_feature=FeatureKey.VOLUME.capitalized)

    def test_a_sequence_beyond_the_limit_names_the_limit(
        self,
        blank_inputs: SequenceInputs,
        bound_themes: List[str],
    ) -> None:
        blank_inputs.show(ChannelName.PULSE1, FeatureKey.VOLUME, sequence(300))
        message = blank_inputs.status_message(ChannelName.PULSE1, FeatureKey.VOLUME)
        assert "300" in message
        assert str(MAX_SEQUENCE_ITEMS) in message


class TestTheExportsASequenceStatusNames(BaseTestSuite):
    """Every tracker export stores a bounded number of items, so the status line names each export
    that shortens the dimension beside what it keeps, and leaves out the ones that store it whole.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        feature_key: FeatureKey
        item_count: int
        expected: FrozenSet[ExportFormat]

    test_cases = (
        TestCase(
            feature_key=FeatureKey.VOLUME,
            item_count=PAST_A_SEQUENCE,
            expected=frozenset({ExportFormat.FAMITRACKER}),
            label="volume_past_a_sequence",
        ),
        TestCase(
            feature_key=FeatureKey.VOLUME,
            item_count=PAST_A_MACRO,
            expected=frozenset(
                {
                    ExportFormat.FAMITRACKER,
                    ExportFormat.BITPHASE,
                    ExportFormat.BITPHASE_PRESET,
                }
            ),
            label="volume_past_a_macro",
        ),
        TestCase(
            feature_key=FeatureKey.ARPEGGIO,
            item_count=PAST_A_MACRO,
            expected=frozenset(
                {
                    ExportFormat.FAMITRACKER,
                    ExportFormat.BITPHASE_PRESET,
                }
            ),
            label="arpeggio_past_a_macro",
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_status_names_each_export_that_shortens_the_dimension(
        self,
        blank_inputs: SequenceInputs,
        test_case: TestCase,
    ) -> None:
        envelope = sequence(test_case.item_count)
        blank_inputs.show(ChannelName.PULSE1, test_case.feature_key, envelope)

        message = blank_inputs.status_message(ChannelName.PULSE1, test_case.feature_key)

        named = {
            export_format
            for export_format, stored_length in FORMAT_STORED_LENGTHS.items()
            if LANGUAGE_MANAGER[KEPT_KEYS[export_format]].format(
                limit=stored_length(test_case.feature_key, envelope),
            )
            in message
        }
        assert named == test_case.expected
        assert str(test_case.item_count) in message
