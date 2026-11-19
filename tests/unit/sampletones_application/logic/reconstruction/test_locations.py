from dataclasses import dataclass
from pathlib import Path

import pytest

from sampletones_application.logic.reconstruction.locations import audio_location, file_location
from sampletones_application.view_model.reconstruction.paths.state import ReconstructionPathState
from tests.suite.case import BaseRegularTestCase


class TestTheOriginalAudioLocation:
    @dataclass(frozen=True, kw_only=True)
    class AudioPathCase(BaseRegularTestCase):
        has_filepath: bool
        has_content: bool
        expected: ReconstructionPathState

    test_cases = (
        AudioPathCase(
            label="detached",
            has_filepath=False,
            has_content=False,
            expected=ReconstructionPathState.NOT_APPLICABLE,
        ),
        AudioPathCase(
            label="recorded_but_unavailable",
            has_filepath=True,
            has_content=False,
            expected=ReconstructionPathState.NOT_FOUND,
        ),
        AudioPathCase(
            label="available",
            has_filepath=True,
            has_content=True,
            expected=ReconstructionPathState.AVAILABLE,
        ),
    )

    @pytest.mark.parametrize("case", test_cases, ids=lambda case: case.label)
    def test_audio_path_state_follows_loaded_content(self, case: AudioPathCase) -> None:
        source_paths = (Path("/songs/source.wav"),) if case.has_filepath else ()

        view_model = audio_location(
            source_paths,
            loaded=case.has_content,
        )

        assert view_model.state is case.expected

    def test_stem_paths_report_multiple_state(self) -> None:
        stem_paths = (
            Path("/stems/drums/kick.wav"),
            Path("/stems/drums/snare.wav"),
        )
        view_model = audio_location(
            stem_paths,
            loaded=True,
        )

        assert view_model.state is ReconstructionPathState.MULTIPLE
        assert view_model.paths == tuple(str(path) for path in stem_paths)
        assert view_model.path == ""


class TestTheReconstructionFileLocation:
    def test_a_document_with_no_file_names_none(self) -> None:
        view_model = file_location(None)

        assert (view_model.state, view_model.paths) == (ReconstructionPathState.NOT_APPLICABLE, ())

    def test_a_document_on_a_file_names_it(self) -> None:
        path = Path("/songs/tone.strec")

        view_model = file_location(path)

        assert (view_model.state, view_model.paths) == (ReconstructionPathState.AVAILABLE, (str(path),))

    def test_stems_named_but_unloaded_read_as_missing_whatever_their_count(self) -> None:
        stem_paths = (Path("/stems/kick.wav"), Path("/stems/snare.wav"))

        view_model = audio_location(stem_paths, loaded=False)

        assert (view_model.state, view_model.paths) == (ReconstructionPathState.NOT_FOUND, ())
