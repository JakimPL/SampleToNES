from pathlib import Path
from typing import List

from sampletones_tools.calibration.board.clips import GatheredClips, InPlaceClips, clip_store
from sampletones_tools.calibration.board.layout import AUDIO_DIRECTORY, PAGE_DIRECTORY
from sampletones_tools.calibration.board.reading import read_run, read_runs
from sampletones_tools.calibration.layout import RECORDINGS_DIRECTORY

CLIP = "tone-a.flac"


class TestClipStoreChoice:
    def test_a_page_in_its_own_run_plays_the_clips_where_they_lie(self, run: Path) -> None:
        assert isinstance(clip_store(read_runs([run]), run), InPlaceClips)

    def test_a_page_written_elsewhere_carries_copies(self, run: Path, tmp_path: Path) -> None:
        assert isinstance(clip_store(read_runs([run]), tmp_path / "page"), GatheredClips)

    def test_a_page_over_several_runs_carries_copies(self, runs: List[Path], tmp_path: Path) -> None:
        assert isinstance(clip_store(read_runs(runs), runs[0]), GatheredClips)


class TestInPlaceClips:
    def test_a_clip_is_named_relative_to_the_run(self, run: Path) -> None:
        reading = read_run(run, "run-a")
        source = run / RECORDINGS_DIRECTORY / CLIP

        assert InPlaceClips().href(reading, source) == f"{RECORDINGS_DIRECTORY}/{CLIP}"


class TestGatheredClips:
    def test_a_clip_is_copied_under_the_page_and_named_relative_to_it(self, run: Path, tmp_path: Path) -> None:
        reading = read_run(run, "run-a")
        output = tmp_path / "page"
        output.mkdir()
        source = run / RECORDINGS_DIRECTORY / CLIP

        href = GatheredClips(output=output).href(reading, source)

        assert href == f"{PAGE_DIRECTORY}/{AUDIO_DIRECTORY}/run-a/{RECORDINGS_DIRECTORY}/{CLIP}"
        assert (output / href).read_bytes() == source.read_bytes()
