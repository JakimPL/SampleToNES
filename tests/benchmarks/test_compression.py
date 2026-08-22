from time import process_time
from typing import Final

import pytest

from sampletones_core.project.project import Project
from sampletones_player.compression.encode import encode_planes
from sampletones_player.compression.options import EVERY_LAYER
from tests.integration.nsf.corpus import (
    LONG_ARRANGEMENT,
    RECONSTRUCTION,
    RECONSTRUCTION_SECONDS,
    TARGET_SECONDS,
    CorpusEntry,
    arrangement_entry,
    lengthened_arrangement,
    reconstruction_entry,
)

MAX_ENCODER_SECONDS: Final[float] = 30.0


@pytest.fixture(scope="module")
def long_arrangement(integration_project: Project) -> CorpusEntry:
    """The three-minute song an export is measured against."""
    return arrangement_entry(
        LONG_ARRANGEMENT,
        lengthened_arrangement(integration_project, TARGET_SECONDS),
    )


@pytest.fixture(scope="module")
def dense_reconstruction() -> CorpusEntry:
    """The minute of reconstructed audio the encoder works hardest on."""
    return reconstruction_entry(RECONSTRUCTION, RECONSTRUCTION_SECONDS)


class TestTheEncoderKeepsWithinWhatAnExportAllows:
    """The codec runs while the user waits for the file, so its cost is held to a bound."""

    def test_a_three_minute_song_encodes_within_the_budget(
        self,
        long_arrangement: CorpusEntry,
    ) -> None:
        """The bound stands where an export would keep the user waiting, well above today's reading."""
        planes = long_arrangement.planes
        started = process_time()
        encode_planes(
            planes,
            long_arrangement.seeds,
            options=EVERY_LAYER,
            boundaries=frozenset(),
        )
        assert process_time() - started < MAX_ENCODER_SECONDS

    def test_a_reconstruction_encodes_within_the_budget(
        self,
        dense_reconstruction: CorpusEntry,
    ) -> None:
        """A song offering no phrases leans wholly on the search, which is where the cost is."""
        planes = dense_reconstruction.planes
        started = process_time()
        encode_planes(
            planes,
            dense_reconstruction.seeds,
            options=EVERY_LAYER,
            boundaries=frozenset(),
        )
        assert process_time() - started < MAX_ENCODER_SECONDS
