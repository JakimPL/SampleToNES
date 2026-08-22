from dataclasses import dataclass
from pathlib import Path

import pytest

from sampletones_application.view_model.reconstruction.paths.path import (
    ReconstructionPathViewModel,
)
from sampletones_application.view_model.reconstruction.paths.state import (
    ReconstructionPathState,
)
from sampletones_application.view_model.reconstruction.reconstruction import (
    ReconstructionViewModel,
)
from sampletones_application.view_model.reconstruction.stems import (
    ReconstructionStemsViewModel,
)
from sampletones_application.view_model.shared.stems import StemsListViewModel
from sampletones_core.constants.enums import HierarchyMode

EMPTY_STEMS = StemsListViewModel(
    rows=(),
    channels_in_play=(),
    muted_channels=frozenset(),
    live=True,
    collapse_levels=False,
)


@dataclass(frozen=True)
class EnablementCase:
    label: str
    original_audio_state: ReconstructionPathState
    reconstruction_loaded: bool
    audio_source_enabled: bool
    locate_audio_enabled: bool
    show_locate_audio_hint: bool


enablement_cases = [
    EnablementCase(
        "audio_file_present",
        original_audio_state=ReconstructionPathState.AVAILABLE,
        reconstruction_loaded=True,
        audio_source_enabled=True,
        locate_audio_enabled=True,
        show_locate_audio_hint=False,
    ),
    EnablementCase(
        "stems_recorded",
        original_audio_state=ReconstructionPathState.MULTIPLE,
        reconstruction_loaded=True,
        audio_source_enabled=True,
        locate_audio_enabled=True,
        show_locate_audio_hint=False,
    ),
    EnablementCase(
        "audio_file_moved",
        original_audio_state=ReconstructionPathState.NOT_FOUND,
        reconstruction_loaded=True,
        audio_source_enabled=False,
        locate_audio_enabled=True,
        show_locate_audio_hint=False,
    ),
    EnablementCase(
        "detached_from_origin",
        original_audio_state=ReconstructionPathState.NOT_APPLICABLE,
        reconstruction_loaded=True,
        audio_source_enabled=False,
        locate_audio_enabled=False,
        show_locate_audio_hint=True,
    ),
    EnablementCase(
        "nothing_loaded",
        original_audio_state=ReconstructionPathState.EMPTY,
        reconstruction_loaded=False,
        audio_source_enabled=False,
        locate_audio_enabled=False,
        show_locate_audio_hint=False,
    ),
]


class TestReconstructionViewModelEnablement:
    """The original-audio path state drives the source toggle, the locate button,
    and its explanatory hint; the hint accompanies exactly the disabled button of
    a loaded reconstruction that keeps no original audio path."""

    @pytest.mark.parametrize(
        "case",
        enablement_cases,
        ids=lambda case: case.label,
    )
    def test_enablement_follows_original_audio_state(
        self,
        case: EnablementCase,
    ) -> None:
        view_model = ReconstructionViewModel(
            reconstruction_loaded=case.reconstruction_loaded,
            playing_channels=frozenset(),
            selected_channels=frozenset(),
            reconstruction_file=ReconstructionPathViewModel(state=ReconstructionPathState.EMPTY, paths=()),
            original_audio=ReconstructionPathViewModel(state=case.original_audio_state, paths=()),
        )

        assert view_model.audio_source_enabled is case.audio_source_enabled
        assert view_model.locate_audio_enabled is case.locate_audio_enabled
        assert view_model.show_locate_audio_hint is case.show_locate_audio_hint


class TestReconstructionPathViewModelPath:
    def test_single_path_is_the_location(self) -> None:
        view_model = ReconstructionPathViewModel(
            state=ReconstructionPathState.AVAILABLE,
            paths=("/songs/source.wav",),
        )

        assert view_model.path == "/songs/source.wav"

    def test_several_paths_leave_no_single_location(self) -> None:
        view_model = ReconstructionPathViewModel(
            state=ReconstructionPathState.MULTIPLE,
            paths=("/a/one.wav", "/b/two.wav"),
        )

        assert view_model.path == ""


class TestReconstructionPathStateFromSourcePaths:
    def test_no_paths_are_not_applicable(self) -> None:
        assert ReconstructionPathState.from_source_paths(()) is ReconstructionPathState.NOT_APPLICABLE

    def test_one_path_is_available(self) -> None:
        assert (
            ReconstructionPathState.from_source_paths((Path("/songs/source.wav"),)) is ReconstructionPathState.AVAILABLE
        )

    def test_several_paths_are_multiple(self) -> None:
        paths = (Path("/a/one.wav"), Path("/b/two.wav"))

        assert ReconstructionPathState.from_source_paths(paths) is ReconstructionPathState.MULTIPLE


class TestReconstructionStemsViewModel:
    def test_the_setup_line_follows_the_stems_record(self) -> None:
        stems = ReconstructionStemsViewModel(
            reconstruction_loaded=True,
            stems=EMPTY_STEMS,
            hierarchy_mode=HierarchyMode.STRICT,
            channel_cap=2,
        )

        assert stems.show_setup_line
        assert stems.channel_cap == 2

    def test_the_empty_state_names_a_loaded_reconstruction_with_no_source(self) -> None:
        loaded = ReconstructionStemsViewModel(
            reconstruction_loaded=True,
            stems=EMPTY_STEMS,
        )
        closed = ReconstructionStemsViewModel(
            reconstruction_loaded=False,
            stems=EMPTY_STEMS,
        )

        assert loaded.show_empty_state
        assert not loaded.show_setup_line
        assert not closed.show_empty_state
