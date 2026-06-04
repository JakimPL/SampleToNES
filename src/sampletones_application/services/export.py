from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Tuple

import numpy as np

from sampletones_application.services.base import ServiceBase
from sampletones_application.utils.thread import SingleThreadExecutor
from sampletones_core.audio import write_wave
from sampletones_core.exporters import Features
from sampletones_shared.logger import logger


class ExportKind(str, Enum):
    WAV = "wav"
    INSTRUMENT = "instrument"
    INSTRUMENTS = "instruments"


@dataclass(frozen=True)
class ExportSuccess:
    kind: ExportKind
    filepath: Path


@dataclass(frozen=True, eq=False)
class ExportError:
    kind: ExportKind
    exception: Exception


ExportResult = ExportSuccess | ExportError


class ExportService(ServiceBase[ExportResult]):
    def __init__(self, priority: int = 0) -> None:
        super().__init__(priority)
        self._executor = SingleThreadExecutor()

    def export_wav(
        self,
        filepath: Path,
        sample_rate: int,
        audio: np.ndarray,
    ) -> None:
        def task() -> None:
            try:
                write_wave(filepath, sample_rate, audio)
                logger.info(f"Exported reconstruction to WAV: {logger.format_path(filepath)}")
                self._emit(ExportSuccess(kind=ExportKind.WAV, filepath=filepath))
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.error_with_traceback(exc, f"Failed to export reconstruction to WAV: {filepath}")
                self._emit(ExportError(kind=ExportKind.WAV, exception=exc))

        self._executor.execute(task, wait=False)

    def export_instrument(
        self,
        filepath: Path,
        instrument_name: str,
        feature: Features,
    ) -> None:
        def task() -> None:
            try:
                feature.save(filepath, instrument_name)
                logger.info(f"Exported instrument feature to FTI: {logger.format_path(filepath)}")
                self._emit(ExportSuccess(kind=ExportKind.INSTRUMENT, filepath=filepath))
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.error_with_traceback(exc, f"Failed to export instrument: {filepath}")
                self._emit(ExportError(kind=ExportKind.INSTRUMENT, exception=exc))

        self._executor.execute(task, wait=False)

    def export_instruments(
        self,
        directory: Path,
        exports: List[Tuple[Path, str, Features]],
    ) -> None:
        def task() -> None:
            try:
                directory.mkdir(parents=True, exist_ok=True)
                for filepath, instrument_name, feature in exports:
                    feature.save(filepath, instrument_name)
                    logger.info(f"Exported instrument to FTI: {logger.format_path(filepath)}")
                self._emit(ExportSuccess(kind=ExportKind.INSTRUMENTS, filepath=directory))
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.error_with_traceback(exc, f"Failed to export instruments to: {directory}")
                self._emit(ExportError(kind=ExportKind.INSTRUMENTS, exception=exc))

        self._executor.execute(task, wait=False)
