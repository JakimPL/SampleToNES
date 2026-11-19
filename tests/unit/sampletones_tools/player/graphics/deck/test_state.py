from dataclasses import dataclass
from typing import Dict, Final, Type, Union

import pytest
from pydantic import BaseModel, ValidationError

from sampletones_core.constants.general import DUTY_CYCLES, MAX_VOLUME, NUM_PERIODS
from sampletones_shared.constants.music import LIMIT_MAX_PITCH, LIMIT_MIN_PITCH
from sampletones_tools.player.graphics.deck.groups import BAR_GROUP
from sampletones_tools.player.graphics.deck.state import (
    DUTY_COUNT,
    LAST_PITCH,
    MAX_LEVEL,
    NOISE_PERIOD_COUNT,
    DeckState,
    NoiseState,
    PulseState,
    Transport,
    TriangleState,
)
from sampletones_tools.player.graphics.sheet.groups import PatternTable
from sampletones_tools.player.graphics.sheet.sheet import TileSheet
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

StateValue = Union[int, str, Dict[str, int]]

PULSE: Final[Dict[str, int]] = {"duty": DUTY_COUNT - 1, "level": MAX_LEVEL, "pitch": LAST_PITCH}
TRIANGLE: Final[Dict[str, int]] = {"sounding": True, "pitch": LAST_PITCH}
NOISE: Final[Dict[str, int]] = {"level": MAX_LEVEL, "period": NOISE_PERIOD_COUNT - 1, "short": True}
DECK: Final[Dict[str, StateValue]] = {
    "title": "Title",
    "artist": "Artist",
    "copyright": "Copyright",
    "pulse1": PULSE,
    "pulse2": PULSE,
    "triangle": TRIANGLE,
    "noise": NOISE,
    "played_seconds": 0,
    "total_seconds": 0,
    "progress": 0,
    "transport": Transport.PLAYING.value,
    "shimmer": False,
}


@dataclass(frozen=True, kw_only=True)
class StateCase(BaseRegularTestCase):
    model: Type[BaseModel]
    stated: Dict[str, StateValue]


class TestAStateAtItsBounds(BaseTestSuite):
    test_cases = (
        StateCase(model=PulseState, stated={**PULSE}, label="the loudest, highest pulse of the widest duty"),
        StateCase(model=PulseState, stated={"duty": 0, "level": 0, "pitch": 0}, label="the lowest pulse at rest"),
        StateCase(model=TriangleState, stated={**TRIANGLE}, label="the highest triangle"),
        StateCase(model=NoiseState, stated={**NOISE}, label="the loudest noise of the last period"),
        StateCase(model=DeckState, stated=DECK, label="a whole screen"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_it_is_held_as_stated(self, test_case: StateCase) -> None:
        assert test_case.model.model_validate(test_case.stated).model_dump(mode="json") == test_case.stated


class TestAStateTheModelRefuses(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        model: Type[BaseModel]
        stated: Dict[str, StateValue]
        expected: str

    test_cases = (
        TestCase(
            model=PulseState,
            stated={**PULSE, "duty": DUTY_COUNT},
            expected="duty",
            label="a duty past the last",
        ),
        TestCase(model=PulseState, stated={**PULSE, "duty": -1}, expected="duty", label="a duty before the first"),
        TestCase(
            model=PulseState,
            stated={**PULSE, "level": MAX_LEVEL + 1},
            expected="level",
            label="a pulse louder than the loudest",
        ),
        TestCase(model=PulseState, stated={**PULSE, "level": -1}, expected="level", label="a pulse below rest"),
        TestCase(
            model=PulseState,
            stated={**PULSE, "pitch": LAST_PITCH + 1},
            expected="pitch",
            label="a pulse above the highest pitch",
        ),
        TestCase(
            model=TriangleState,
            stated={**TRIANGLE, "pitch": LAST_PITCH + 1},
            expected="pitch",
            label="a triangle above the highest pitch",
        ),
        TestCase(
            model=TriangleState,
            stated={**TRIANGLE, "pitch": -1},
            expected="pitch",
            label="a triangle below the lowest pitch",
        ),
        TestCase(
            model=NoiseState,
            stated={**NOISE, "level": MAX_LEVEL + 1},
            expected="level",
            label="a noise louder than the loudest",
        ),
        TestCase(
            model=NoiseState,
            stated={**NOISE, "period": NOISE_PERIOD_COUNT},
            expected="period",
            label="a period past the last",
        ),
        TestCase(
            model=NoiseState, stated={**NOISE, "period": -1}, expected="period", label="a period before the first"
        ),
        TestCase(
            model=DeckState,
            stated={**DECK, "played_seconds": -1},
            expected="played_seconds",
            label="a time played before the start",
        ),
        TestCase(
            model=DeckState,
            stated={**DECK, "total_seconds": -1},
            expected="total_seconds",
            label="a length below nothing",
        ),
        TestCase(
            model=DeckState, stated={**DECK, "progress": -1}, expected="progress", label="a bar emptier than empty"
        ),
        TestCase(
            model=DeckState,
            stated={**DECK, "transport": "rewinding"},
            expected="transport",
            label="a transport the screen has no glyph for",
        ),
        TestCase(
            model=DeckState,
            stated={**DECK, "pulse1": {**PULSE, "level": MAX_LEVEL + 1}},
            expected="pulse1.level",
            label="a channel outside its own bounds",
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_refusal_names_the_field(self, test_case: TestCase) -> None:
        with pytest.raises(ValidationError, match=test_case.expected):
            test_case.model.model_validate(test_case.stated)


class TestTheBoundsOfAState(BaseTestSuite):
    """A state is bounded by what the console's channels can sound, as the application states it."""

    def test_the_loudest_level_is_the_loudest_volume_a_channel_takes(self) -> None:
        assert MAX_LEVEL == MAX_VOLUME

    def test_a_pulse_chooses_among_the_duty_cycles_the_console_plays(self) -> None:
        assert DUTY_COUNT == len(DUTY_CYCLES)

    def test_the_noise_chooses_among_the_periods_the_console_plays(self) -> None:
        assert NOISE_PERIOD_COUNT == NUM_PERIODS

    def test_the_pitches_run_from_the_lowest_to_the_highest_the_application_reaches(self) -> None:
        assert LIMIT_MIN_PITCH + LAST_PITCH == LIMIT_MAX_PITCH


class TestTheTransport(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        transport: Transport

    test_cases = (
        TestCase(transport=Transport.PLAYING, label="playing"),
        TestCase(transport=Transport.PAUSED, label="paused"),
        TestCase(transport=Transport.STOPPED, label="stopped"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_it_is_named_by_a_glyph_the_shipped_bar_draws(self, test_case: TestCase, shipped_sheet: TileSheet) -> None:
        bar = shipped_sheet.table(PatternTable.BACKGROUND)[BAR_GROUP]

        assert test_case.transport.value in bar.members

    def test_every_state_of_the_song_shows_another_glyph(self, shipped_sheet: TileSheet) -> None:
        tiles = {shipped_sheet.tile(PatternTable.BACKGROUND, BAR_GROUP, transport.value) for transport in Transport}

        assert len(tiles) == len(Transport)
