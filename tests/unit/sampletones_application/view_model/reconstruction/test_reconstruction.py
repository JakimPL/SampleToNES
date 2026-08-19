from dataclasses import dataclass

import pytest

from sampletones_application.view_model.reconstruction.reconstruction import (
    ReconstructionPathState,
    ReconstructionPathViewModel,
    ReconstructionViewModel,
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
            reconstruction_file=ReconstructionPathViewModel(state=ReconstructionPathState.EMPTY, path=""),
            original_audio=ReconstructionPathViewModel(state=case.original_audio_state, path=""),
        )

        assert view_model.audio_source_enabled is case.audio_source_enabled
        assert view_model.locate_audio_enabled is case.locate_audio_enabled
        assert view_model.show_locate_audio_hint is case.show_locate_audio_hint
