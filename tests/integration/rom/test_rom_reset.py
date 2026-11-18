from dataclasses import dataclass
from typing import Final

import numpy as np
import pytest

from sampletones_core.project.voices.sample import Sample
from sampletones_player.song import Song
from sampletones_player.specification.binary import BYTE_VALUES, MAX_BYTE_VALUE
from sampletones_player.specification.memory import RAM_SIZE
from sampletones_tools.player.graphics.deck.deck import Deck
from sampletones_tools.player.trace.screen import ScreenTrace
from sampletones_tools.player.trace.trace import RegisterTrace
from tests.integration.nsf.console.session import play_calls_covering
from tests.integration.nsf.header import sample_information
from tests.integration.rom.session import CLEARED_MEMORY, booted, cartridge, cartridge_trace, paused_after, shown
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

MEMORY_SEED: Final[int] = 1985
PAUSE_POINT: Final[int] = 7
FILLED_MEMORY: Final[bytes] = bytes([MAX_BYTE_VALUE]) * RAM_SIZE
SEEDED_MEMORY: Final[bytes] = bytes(np.random.default_rng(MEMORY_SEED).integers(0, BYTE_VALUES, RAM_SIZE).tolist())


class TestTheCartridgeStartsTheSameFromAnyMemory(BaseTestSuite):
    """A console powers on holding whatever its memory held, and the shell clears it before anything reads it.

    The driver and the shell both count on memory reading as zero once the song starts, so a
    cartridge sounds and shows the same whether its memory came up cleared, filled or random.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        memory: bytes

    test_cases = (
        TestCase(label="cleared", memory=CLEARED_MEMORY),
        TestCase(label="filled", memory=FILLED_MEMORY),
        TestCase(label="seeded", memory=SEEDED_MEMORY),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_trace_equals_the_model_s(self, test_case: TestCase, song: Song, sample: Sample) -> None:
        calls = play_calls_covering(song)

        trace = cartridge_trace(song, sample_information(sample.name), calls, memory=test_case.memory)

        assert trace == RegisterTrace.from_song(song, calls)

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_paused_screen_equals_the_trace(
        self, test_case: TestCase, song: Song, sample: Sample, deck: Deck
    ) -> None:
        information = sample_information(sample.name)
        console = booted(cartridge(song, information), memory=test_case.memory)

        paused_after(console, PAUSE_POINT)

        assert shown(console.screen) == ScreenTrace(song, information, deck).paused_after(PAUSE_POINT)
