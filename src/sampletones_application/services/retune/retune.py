from typing import List, Sequence, Tuple

from sampletones_application.services.base import ServiceBase
from sampletones_application.services.result import ServiceError, ServiceSuccess
from sampletones_application.services.retune.result import RetuneResult
from sampletones_application.services.retune.sample import RetunedSample
from sampletones_application.utils.parallelization.coalescing import LatestWinsExecutor
from sampletones_core.reconstructions import Reconstruction

RetuneTarget = Tuple[str, Reconstruction]


class SampleRetuneService(ServiceBase[RetuneResult]):
    """Re-synthesizes embedded samples' stored reconstructions to a new NES frequency.

    Changing the project rate leaves each sample's persistent rendered waveform — the array
    the Reconstructions tab shows for editing — at its old rate; song playback already
    re-renders live, so this only refreshes those editing waveforms. The batch runs on a
    background queue and emits one ``ServiceSuccess(RetunedSample)`` per sample so the caller
    can apply each as it completes.

    Requests run on a :class:`LatestWinsExecutor`, so a fresh rate change supersedes an
    in-flight batch: the newest batch runs once the current one finishes, and the caller
    discards results whose rate no longer matches the project.
    """

    def __init__(self, priority: int = 0) -> None:
        super().__init__(priority)
        self._executor = LatestWinsExecutor()

    def start(self, targets: Sequence[RetuneTarget], nes_frequency: int) -> bool:
        pending = list(targets)
        return self._executor.submit(lambda: self._run(pending, nes_frequency))

    def is_running(self) -> bool:
        return self._executor.is_running

    def _run(self, targets: List[RetuneTarget], nes_frequency: int) -> None:
        try:
            for sample_id, reconstruction in targets:
                retuned = reconstruction.with_nes_frequency(nes_frequency)
                self._emit(ServiceSuccess(value=RetunedSample(sample_id=sample_id, reconstruction=retuned)))
        except Exception as exception:  # pylint: disable=broad-exception-caught
            self._emit(ServiceError(exception=exception))
