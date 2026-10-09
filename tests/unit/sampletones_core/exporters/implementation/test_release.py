from dataclasses import dataclass
from typing import Callable, Final, List, Sequence, Tuple

import pytest

from sampletones_core.constants.general import MAX_VOLUME, MIN_PITCH, SILENT_VOLUME
from sampletones_core.exporters.implementation.noise import NoiseExporter
from sampletones_core.exporters.implementation.pulse import PulseExporter
from sampletones_core.exporters.implementation.triangle import TriangleExporter
from sampletones_core.instructions.implementation.noise import NoiseInstruction
from sampletones_core.instructions.implementation.pulse import PulseInstruction
from sampletones_core.instructions.implementation.triangle import TriangleInstruction
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseAutolabelTestCase

VOLUMES: Final[int] = 2

SOUNDING: Final[int] = 12
LOUDER: Final[int] = 15


def pulse_volumes(levels: Sequence[int]) -> List[int]:
    instructions = [
        PulseInstruction(on=level > SILENT_VOLUME, pitch=MIN_PITCH, volume=level, duty_cycle=0) for level in levels
    ]
    return PulseExporter.extract_data(instructions)[VOLUMES]


def triangle_volumes(levels: Sequence[int]) -> List[int]:
    instructions = [TriangleInstruction(on=level > SILENT_VOLUME, pitch=MIN_PITCH) for level in levels]
    return TriangleExporter.extract_data(instructions)[VOLUMES]


def noise_volumes(levels: Sequence[int]) -> List[int]:
    instructions = [NoiseInstruction(on=level > SILENT_VOLUME, period=0, volume=level, short=False) for level in levels]
    return NoiseExporter.extract_data(instructions)[VOLUMES]


class TestTheReleaseEveryGeneratorWrites(BaseTestSuite):
    """A channel that stops sounding writes the silence that stops it.

    A FamiTracker sequence halts on its last item and holds that value for as long as the note
    sounds, so a volume envelope whose frames end audible carries one silent item past them to
    release the note. Every generator writes that item, which is what a reader edits in the
    instruments panel and what an export keeps within the items the file holds.
    """

    @dataclass(frozen=True, kw_only=True)
    class Writer(BaseAutolabelTestCase):
        """One channel's exporter, and the level a sounding frame reaches it at.

        The triangle plays at one level, so a frame there is audible or silent rather than graded,
        and a case states its levels once for every channel to read what it can of.
        """

        expected: str
        volumes: Callable[[Sequence[int]], List[int]]
        plays_at_one_level: bool

        @property
        def label(self) -> str:
            return self.expected

        def written(self, level: int) -> int:
            """The value this channel writes for a frame stated at ``level``."""
            if level == SILENT_VOLUME:
                return SILENT_VOLUME

            return MAX_VOLUME if self.plays_at_one_level else level

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        expected: Tuple[int, ...]
        levels: Tuple[int, ...]
        ending: str

        @property
        def label(self) -> str:
            return self.ending

    writers = (
        Writer(expected="pulse", volumes=pulse_volumes, plays_at_one_level=False),
        Writer(expected="triangle", volumes=triangle_volumes, plays_at_one_level=True),
        Writer(expected="noise", volumes=noise_volumes, plays_at_one_level=False),
    )

    test_cases = (
        TestCase(
            ending="ends_sounding",
            levels=(SOUNDING, SOUNDING),
            expected=(SOUNDING, SOUNDING, SILENT_VOLUME),
        ),
        TestCase(
            ending="ends_silent",
            levels=(SOUNDING, SILENT_VOLUME),
            expected=(SOUNDING, SILENT_VOLUME),
        ),
        TestCase(
            ending="one_sounding_frame",
            levels=(SOUNDING,),
            expected=(SOUNDING, SILENT_VOLUME),
        ),
        TestCase(
            ending="nothing_written",
            levels=(),
            expected=(),
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    @pytest.mark.parametrize("writer", writers, ids=lambda writer: writer.label)
    def test_the_volume_written_ends_where_the_channel_stops_sounding(
        self,
        writer: Writer,
        test_case: TestCase,
    ) -> None:
        expected = tuple(writer.written(level) for level in test_case.expected)
        assert tuple(writer.volumes(test_case.levels)) == expected

    @pytest.mark.parametrize("writer", writers, ids=lambda writer: writer.label)
    def test_a_louder_ending_releases_the_same_way(self, writer: Writer) -> None:
        """The release follows from the channel going quiet, whatever level it went quiet from."""
        assert writer.volumes((SOUNDING, LOUDER))[-1] == SILENT_VOLUME
