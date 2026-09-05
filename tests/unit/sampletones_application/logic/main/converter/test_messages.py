from dataclasses import dataclass
from pathlib import Path
from typing import Final, Optional, Tuple

import pytest

from sampletones_application.services.conversion.result import (
    ConversionItem,
    ReconstructionStep,
)
from sampletones_application.services.result import ServiceProgress
from sampletones_application.view_model.main.converter import ConversionPhase
from sampletones_core.reconstructions.stage import ReconstructionStage
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.unit.sampletones_application.logic.main.converter.texts import TEXTS, messages

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


class TestProgressText(BaseTestSuite):
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


class TestActionLabel(BaseTestSuite):
    """The button says what the run writes.

    One recording names its document, several are counted, and the count reads as a mix or as a run
    of its own depending on the output switch, so the switch and the button read as one sentence.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        phase: ConversionPhase
        mixes: bool
        converted: Tuple[Path, ...]
        expected: str

    test_cases = (
        TestCase(
            label="nothing_gathered_offers_the_bare_label",
            phase=ConversionPhase.IDLE,
            mixes=False,
            converted=(),
            expected=TEXTS["main.converter.label.convert_button"],
        ),
        TestCase(
            label="one_recording_names_its_document",
            phase=ConversionPhase.IDLE,
            mixes=False,
            converted=(Path("/audio/kick.wav"),),
            expected=TEXTS["main.converter.template.convert_recording"].format(name="kick"),
        ),
        TestCase(
            label="a_mix_of_one_names_it_too",
            phase=ConversionPhase.IDLE,
            mixes=True,
            converted=(Path("/audio/kick.wav"),),
            expected=TEXTS["main.converter.template.convert_recording"].format(name="kick"),
        ),
        TestCase(
            label="several_recordings_are_counted",
            phase=ConversionPhase.IDLE,
            mixes=False,
            converted=(Path("/audio/kick.wav"), Path("/audio/snare.wav"), Path("/audio/hat.wav")),
            expected=TEXTS["main.converter.template.convert_recordings"].format(count=3),
        ),
        TestCase(
            label="several_mixed_recordings_read_as_a_mix",
            phase=ConversionPhase.IDLE,
            mixes=True,
            converted=(Path("/audio/kick.wav"), Path("/audio/snare.wav"), Path("/audio/hat.wav")),
            expected=TEXTS["main.converter.template.mix_recordings"].format(count=3),
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_label_says_what_the_run_writes(self, test_case: TestCase) -> None:
        label = messages().action_label(
            phase=test_case.phase,
            mixes=test_case.mixes,
            converted=test_case.converted,
        )

        assert label == test_case.expected

    @pytest.mark.parametrize(
        "phase",
        [ConversionPhase.WAITING, ConversionPhase.RUNNING, ConversionPhase.CANCELLING],
    )
    def test_a_conversion_holding_resources_reads_the_cancel_label(self, phase: ConversionPhase) -> None:
        label = messages().action_label(
            phase=phase,
            mixes=False,
            converted=(Path("/audio/kick.wav"),),
        )

        assert label == TEXTS["main.converter.label.cancel_button"]
