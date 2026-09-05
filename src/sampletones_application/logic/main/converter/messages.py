from pathlib import Path
from typing import Dict, Final, Optional

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.services.conversion.result import ConversionItem
from sampletones_application.services.result import ServiceProgress
from sampletones_application.view_model.main.converter import ACTIVE_PHASES, ConversionPhase
from sampletones_core.parallelization import ETAEstimator
from sampletones_core.reconstructions.stage import ReconstructionStage

SINGLE_JOB: Final[int] = 1


class ConverterMessages:
    """What the converter puts to a reader: the line under the bar and the label on its button.

    Every phrase the panel shows is composed here, so the words a run reports and the words a
    settled setup reports read as one voice and the keys they come from stand in one place.
    """

    def __init__(self, language_manager: LanguageManager) -> None:
        self._language_manager = language_manager
        self.idle: str = language_manager["main.converter.message.status_idle"]
        self.waiting: str = language_manager["main.converter.message.status_waiting"]
        self.generating_library: str = language_manager["main.converter.message.status_generating_library"]
        self.cancelling: str = language_manager["main.converter.message.status_cancelling"]
        self.canceled: str = language_manager["main.converter.message.status_canceled"]
        self.completed: str = language_manager["main.converter.message.status_reconstruction_completed"]
        self.failed: str = language_manager["main.converter.message.status_error"]
        self._stages: Dict[ReconstructionStage, str] = {
            ReconstructionStage.LOADING: language_manager["main.converter.message.stage_loading"],
            ReconstructionStage.MATCHING: language_manager["main.converter.message.stage_matching"],
            ReconstructionStage.DECODING: language_manager["main.converter.message.stage_decoding"],
            ReconstructionStage.RENDERING: language_manager["main.converter.message.stage_rendering"],
        }

    def progress_text(
        self,
        progress: ServiceProgress[ConversionItem],
        reconstruction_name: str,
    ) -> str:
        """What the run is doing, how far it has come, and how long it has left.

        A batch is many reconstructions and a count says where it stands; a single job counts to
        one, so it names the document it is writing instead. Either way the reconstruction under
        way says which stage it is in, which is the whole of what a reader watching one job has.
        """
        return (
            self._run_text(progress, reconstruction_name) + self._stage_text(progress) + self._estimate_text(progress)
        )

    def action_label(
        self,
        *,
        phase: ConversionPhase,
        stems_mode: bool,
        is_file: bool,
        input_path: Optional[Path],
        playing: int,
    ) -> str:
        """The label the single action button shows: the cancel label while a conversion holds
        resources, otherwise the convert label named after what it would convert."""
        if phase in ACTIVE_PHASES:
            return self._language_manager["main.converter.label.cancel_button"]

        if stems_mode:
            return self._mix_label(playing)

        base = (
            self._language_manager["main.converter.label.convert_sample_button"]
            if is_file
            else self._language_manager["main.converter.label.convert_directory_button"]
        )
        if input_path is None:
            return base

        return self._named_label(base, input_path.name)

    def _mix_label(self, playing: int) -> str:
        """The stems label, named after how many recordings take part."""
        base = self._language_manager["main.converter.label.convert_stems_button"]
        if not playing:
            return base

        return self._named_label(base, str(playing))

    def _named_label(self, base: str, subject: str) -> str:
        return self._language_manager["main.converter.template.convert_label_template"].format(base, subject)

    def _run_text(
        self,
        progress: ServiceProgress[ConversionItem],
        reconstruction_name: str,
    ) -> str:
        if progress.total > SINGLE_JOB:
            return self._language_manager["main.converter.template.progress_template"].format(
                progress.completed, progress.total
            )

        return self._language_manager["main.converter.template.single_progress_template"].format(reconstruction_name)

    def _stage_text(self, progress: ServiceProgress[ConversionItem]) -> str:
        step = progress.current_item.step if progress.current_item is not None else None
        if step is None:
            return ""

        return self._language_manager["main.converter.template.stage_template"].format(
            stage=self._stages[step.stage],
            completed=step.completed,
            total=step.total,
        )

    def _estimate_text(self, progress: ServiceProgress[ConversionItem]) -> str:
        eta_string = ETAEstimator.format_duration(progress.eta_seconds)
        if not eta_string:
            return ""

        return self._language_manager["global.dialog.template.time_estimation"].format(eta_string=eta_string)
