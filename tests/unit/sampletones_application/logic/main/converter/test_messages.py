from pathlib import Path
from typing import Final, Optional

import pytest

from sampletones_application.services.conversion.result import (
    ConversionItem,
    ReconstructionStep,
)
from sampletones_application.services.result import ServiceProgress
from sampletones_application.view_model.main.converter import ConversionPhase
from sampletones_core.reconstructions.stage import ReconstructionStage
from tests.unit.sampletones_application.logic.main.converter.texts import messages

FRAMES: Final[int] = 1100


def _progress(
    completed: int,
    total: int,
    item: Optional[ConversionItem] = None,
    partial: float = 0.0,
) -> ServiceProgress[ConversionItem]:
    return ServiceProgress(
        completed=completed,
        total=total,
        eta_seconds=None,
        current_item=item,
        partial=partial,
    )


def _item(stage: ReconstructionStage, completed: int) -> ConversionItem:
    return ConversionItem(
        source=Path("/audio/kick.wav"),
        step=ReconstructionStep(stage=stage, completed=completed, total=FRAMES),
    )


class TestProgressText:
    """A batch counts the files it has written; a single job names the reconstruction it is making."""

    def test_a_batch_counts_its_files(self) -> None:
        assert messages().progress_text(_progress(2, 5), "track") == "Progress: 2/5 files"

    def test_a_single_job_names_the_reconstruction_it_writes(self) -> None:
        assert messages().progress_text(_progress(0, 1), "track") == "Reconstructing track..."

    def test_the_status_names_the_stage_and_its_counts(self) -> None:
        progress = _progress(0, 1, item=_item(ReconstructionStage.MATCHING, 412), partial=0.35)

        assert messages().progress_text(progress, "kick") == "Reconstructing kick... - matching 412/1100"

    def test_a_run_yet_to_say_anything_still_names_its_recording(self) -> None:
        progress = _progress(0, 1, item=ConversionItem(source=Path("/audio/kick.wav")))

        assert messages().progress_text(progress, "kick") == "Reconstructing kick..."

    def test_a_batch_counts_the_reconstruction_under_way_toward_its_files(self) -> None:
        progress = _progress(2, 5, item=_item(ReconstructionStage.RENDERING, FRAMES), partial=0.5)

        assert messages().progress_text(progress, "kick") == "Progress: 2/5 files - rendering 1100/1100"


class TestActionLabel:
    """The one action button's label is a projection of converter state, composed where the display
    strings are resolved (the logic layer) rather than glued together in the panel: it names the
    selected input while idle and reads the cancel label once a conversion holds resources.
    """

    def test_a_file_names_the_recording_it_would_convert(self) -> None:
        label = messages().action_label(
            phase=ConversionPhase.IDLE,
            stems_mode=False,
            is_file=True,
            input_path=Path("/audio/kick.wav"),
            playing=0,
        )

        assert label == "Convert sample: kick.wav"

    def test_a_directory_uses_the_directory_variant(self) -> None:
        label = messages().action_label(
            phase=ConversionPhase.IDLE,
            stems_mode=False,
            is_file=False,
            input_path=Path("/audio/drums"),
            playing=0,
        )

        assert label == "Convert directory: drums"

    def test_nothing_picked_reads_the_bare_convert_label(self) -> None:
        label = messages().action_label(
            phase=ConversionPhase.IDLE,
            stems_mode=False,
            is_file=True,
            input_path=None,
            playing=0,
        )

        assert label == "Convert sample"

    def test_a_mix_names_how_many_recordings_take_part(self) -> None:
        label = messages().action_label(
            phase=ConversionPhase.IDLE,
            stems_mode=True,
            is_file=True,
            input_path=Path("/audio/kick.wav"),
            playing=3,
        )

        assert label == "Convert stems: 3"

    def test_a_mix_with_nobody_taking_part_reads_the_bare_label(self) -> None:
        label = messages().action_label(
            phase=ConversionPhase.IDLE,
            stems_mode=True,
            is_file=True,
            input_path=None,
            playing=0,
        )

        assert label == "Convert stems"

    @pytest.mark.parametrize(
        "phase",
        [ConversionPhase.WAITING, ConversionPhase.RUNNING, ConversionPhase.CANCELLING],
    )
    def test_a_conversion_holding_resources_reads_the_cancel_label(self, phase: ConversionPhase) -> None:
        label = messages().action_label(
            phase=phase,
            stems_mode=False,
            is_file=True,
            input_path=Path("/audio/kick.wav"),
            playing=0,
        )

        assert label == "Cancel"
