from time import process_time
from typing import Final

import pytest

from sampletones_core.project.project import Project
from sampletones_player.compression.encode import encode_planes
from sampletones_player.compression.options import CodecOptions
from tests.integration.nsf.corpus import (
    LONG_ARRANGEMENT,
    TARGET_SECONDS,
    CorpusEntry,
    arrangement_entry,
    lengthened_arrangement,
)

EVERY_LAYER: Final[CodecOptions] = CodecOptions(
    holds=True,
    phrases=True,
    transposition=True,
    search=True,
)
MAX_ENCODER_SECONDS: Final[float] = 30.0


@pytest.fixture(scope="module")
def long_arrangement(integration_project: Project) -> CorpusEntry:
    """The three-minute song an export is measured against."""
    return arrangement_entry(
        LONG_ARRANGEMENT,
        lengthened_arrangement(integration_project, TARGET_SECONDS),
    )


class TestTheEncoderKeepsWithinWhatAnExportAllows:
    """The codec runs while the user waits for the file, so its cost is held to a bound."""

    def test_a_three_minute_song_encodes_within_the_budget(
        self,
        long_arrangement: CorpusEntry,
    ) -> None:
        """The bound stands where an export would keep the user waiting, against five seconds today."""
        planes = long_arrangement.planes
        started = process_time()
        encode_planes(
            planes,
            long_arrangement.seeds,
            options=EVERY_LAYER,
            boundaries=frozenset(),
        )
        assert process_time() - started < MAX_ENCODER_SECONDS
