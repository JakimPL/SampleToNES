from dataclasses import dataclass
from enum import StrEnum
from functools import partial
from typing import List, Tuple
from unittest.mock import MagicMock

import pytest

from sampletones_application.application import Application
from sampletones_application.categories.hierarchy import Tab
from sampletones_core.constants.enums import GeneratorName
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase


class Surface(StrEnum):
    """The control a channel is switched by, one per tab that carries one."""

    MAIN = "main"
    RECONSTRUCTIONS = "reconstructions"
    SEQUENCER = "sequencer"


class Harness:
    """An application standing in one tab, recording which surface a channel key reaches."""

    def __init__(self, tab: Tab) -> None:
        self.switched: List[Tuple[Surface, GeneratorName]] = []

        self.application = Application.__new__(Application)
        self.application._shell = MagicMock()
        self.application._shell.get_current_tab.return_value = tab
        self.application._main_tab = MagicMock()
        self.application._main_tab.toggle_generator = partial(self._record, Surface.MAIN)
        self.application._reconstructions_tab = MagicMock()
        self.application._reconstructions_tab.toggle_generator = partial(self._record, Surface.RECONSTRUCTIONS)
        self.application._sequencer_tab = MagicMock()
        self.application._sequencer_tab.toggle_channel = partial(self._record, Surface.SEQUENCER)

    def _record(self, surface: Surface, generator: GeneratorName) -> None:
        self.switched.append((surface, generator))


class TestToggleChannel(BaseTestSuite):
    """One key switches the channel of whichever tab the reader is standing in."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        tab: Tab
        expected: Surface

    test_cases = (
        TestCase(
            label="the main tab switches a generator of the reconstructor",
            tab=Tab.MAIN,
            expected=Surface.MAIN,
        ),
        TestCase(
            label="the reconstructions tab switches a slice of the waveform",
            tab=Tab.RECONSTRUCTIONS,
            expected=Surface.RECONSTRUCTIONS,
        ),
        TestCase(
            label="the sequencer switches its mix",
            tab=Tab.SEQUENCER,
            expected=Surface.SEQUENCER,
        ),
        TestCase(
            label="a tab carrying no control of its own falls to the mix",
            tab=Tab.INSTRUCTIONS,
            expected=Surface.SEQUENCER,
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_the_surface_a_channel_key_reaches(self, test_case: TestCase) -> None:
        harness = Harness(test_case.tab)

        harness.application._toggle_channel(GeneratorName.TRIANGLE)

        assert harness.switched == [(test_case.expected, GeneratorName.TRIANGLE)]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_every_channel_reaches_the_same_surface(self, test_case: TestCase) -> None:
        """The four keys stand together, so a tab answers all of them or none."""
        harness = Harness(test_case.tab)

        for generator in GeneratorName:
            harness.application._toggle_channel(generator)

        assert harness.switched == [(test_case.expected, generator) for generator in GeneratorName]


class TestMuteChannel:
    def test_the_menu_gesture_switches_the_sequencer_mix_from_any_tab(self) -> None:
        """The Channels submenu shows the sequencer's mix, so choosing an item switches that mix."""
        harness = Harness(Tab.MAIN)

        harness.application._mute_channel(GeneratorName.NOISE)

        assert harness.switched == [(Surface.SEQUENCER, GeneratorName.NOISE)]
