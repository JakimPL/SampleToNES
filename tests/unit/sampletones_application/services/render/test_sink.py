from pathlib import Path
from typing import List

import numpy as np
import pytest

from sampletones_application.services.render.constants import SCRATCH_SUFFIX
from sampletones_application.services.render.scratch import ScratchAudio
from sampletones_application.services.render.sink import (
    DirectRenderSink,
    NormalizingRenderSink,
    build_render_sink,
)
from sampletones_shared.exceptions import AudioWriteError
from tests.suite.base import BaseTestSuite
from tests.unit.sampletones_application.services.render.conftest import (
    read_samples,
    wave_spec,
)

KEEP_GOING = True


def _rows(count: int, samples: int, level: float) -> List[np.ndarray]:
    return [np.full(samples, level, dtype=np.float32) for _ in range(count)]


class TestTheSinkIsChosenByTheLevelChoice(BaseTestSuite):
    def test_a_plain_render_writes_straight_out(self, tmp_path: Path) -> None:
        sink = build_render_sink(tmp_path / "song.wav", wave_spec(), normalize=False)

        assert isinstance(sink, DirectRenderSink)

    def test_a_normalized_render_spills_first(self, tmp_path: Path) -> None:
        sink = build_render_sink(tmp_path / "song.wav", wave_spec(), normalize=True)

        assert isinstance(sink, NormalizingRenderSink)


class TestTheSinkOwnsItsFile(BaseTestSuite):
    def test_writing_outside_the_block_is_refused(self, tmp_path: Path) -> None:
        sink = DirectRenderSink(tmp_path / "song.wav", wave_spec())

        with pytest.raises(AudioWriteError, match="write within the sink's context"):
            sink.write(np.zeros(4, dtype=np.float32))

    def test_spilling_outside_the_block_is_refused(self, tmp_path: Path) -> None:
        sink = NormalizingRenderSink(tmp_path / "song.wav", wave_spec())

        with pytest.raises(AudioWriteError, match="write between start and seal"):
            sink.write(np.zeros(4, dtype=np.float32))

    def test_discarding_removes_the_destination(self, tmp_path: Path) -> None:
        destination = tmp_path / "song.wav"
        sink = DirectRenderSink(destination, wave_spec())
        with sink:
            sink.write(np.zeros(64, dtype=np.float32))

        sink.discard()

        assert not destination.exists()

    def test_discarding_a_render_that_never_ran_is_harmless(self, tmp_path: Path) -> None:
        sink = DirectRenderSink(tmp_path / "song.wav", wave_spec())

        sink.discard()

        assert not list(tmp_path.iterdir())


class TestNormalizingSink(BaseTestSuite):
    def _write(self, sink: NormalizingRenderSink, rows: List[np.ndarray]) -> bool:
        with sink:
            for row in rows:
                sink.write(row)

            return sink.finish(lambda _encoded: KEEP_GOING)

    def test_the_loudest_row_sets_the_scale_for_every_row(self, tmp_path: Path) -> None:
        destination = tmp_path / "song.wav"
        sink = NormalizingRenderSink(destination, wave_spec())

        self._write(sink, [*_rows(1, 32, 0.1), *_rows(1, 32, 0.5)])
        written = read_samples(destination)

        assert float(written[:32].max()) == pytest.approx(0.2, abs=1e-4)
        assert float(written[32:].max()) == pytest.approx(1.0, abs=1e-4)

    def test_a_pass_stopped_partway_reports_the_file_unfinished(self, tmp_path: Path) -> None:
        sink = NormalizingRenderSink(tmp_path / "song.wav", wave_spec())

        with sink:
            sink.write(np.full(4, 0.5, dtype=np.float32))
            completed = sink.finish(lambda _encoded: not KEEP_GOING)

        assert not completed

    def test_the_spill_stands_beside_the_destination(self, tmp_path: Path) -> None:
        sink = NormalizingRenderSink(tmp_path / "song.wav", wave_spec())

        with sink:
            sink.write(np.full(4, 0.5, dtype=np.float32))

            assert (tmp_path / f"song.wav{SCRATCH_SUFFIX}").exists()


class TestScratchAudio(BaseTestSuite):
    """The spill file holds what it was given, and reports what it holds."""

    def test_the_samples_read_back_in_the_order_they_were_written(self, tmp_path: Path) -> None:
        scratch = ScratchAudio(tmp_path / "spill")
        written = np.arange(10, dtype=np.float32)

        scratch.start()
        scratch.write(written[:4])
        scratch.write(written[4:])
        scratch.seal()

        assert np.array_equal(np.concatenate(list(scratch.blocks(3))), written)

    def test_the_blocks_are_bounded_by_the_size_asked_for(self, tmp_path: Path) -> None:
        scratch = ScratchAudio(tmp_path / "spill")

        scratch.start()
        scratch.write(np.zeros(10, dtype=np.float32))
        scratch.seal()

        assert [len(block) for block in scratch.blocks(4)] == [4, 4, 2]

    def test_the_peak_spans_every_chunk(self, tmp_path: Path) -> None:
        scratch = ScratchAudio(tmp_path / "spill")

        scratch.start()
        scratch.write(np.full(4, 0.2, dtype=np.float32))
        scratch.write(np.full(4, -0.7, dtype=np.float32))
        scratch.write(np.full(4, 0.3, dtype=np.float32))
        scratch.seal()

        assert scratch.peak == pytest.approx(0.7)
        assert scratch.samples == 12

    def test_sealing_twice_is_harmless(self, tmp_path: Path) -> None:
        scratch = ScratchAudio(tmp_path / "spill")

        scratch.start()
        scratch.seal()
        scratch.seal()

        assert not scratch.samples

    def test_removing_clears_the_spill(self, tmp_path: Path) -> None:
        scratch = ScratchAudio(tmp_path / "spill")

        scratch.start()
        scratch.seal()
        scratch.remove()

        assert not scratch.path.exists()
