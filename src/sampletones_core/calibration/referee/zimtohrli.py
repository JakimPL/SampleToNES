import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Final, Optional

import numpy as np

from sampletones_core.audio.io import write_wave

ZIMTOHRLI_BINARY: Final[str] = "zimtohrli"


class ZimtohrliReferee:
    """
    Psychoacoustic distance judged by an external `zimtohrli` comparison binary.

    Writes both signals as WAV files and reports the last numeric value the binary
    prints for the pair. Availability is checked through `find_zimtohrli`.
    """

    def __init__(self, sample_rate: int, binary: Path) -> None:
        self.sample_rate = sample_rate
        self.binary = binary

    @property
    def name(self) -> str:
        return "zimtohrli"

    def score(self, reference: np.ndarray, estimate: np.ndarray) -> float:
        with tempfile.TemporaryDirectory() as directory:
            reference_path = Path(directory) / "reference.wav"
            estimate_path = Path(directory) / "estimate.wav"
            write_wave(reference_path, self.sample_rate, reference)
            write_wave(estimate_path, self.sample_rate, estimate)
            completed = subprocess.run(
                [str(self.binary), str(reference_path), str(estimate_path)],
                capture_output=True,
                text=True,
                check=True,
            )

        values = [token for token in completed.stdout.split() if self._is_float(token)]
        if not values:
            raise ValueError(f"zimtohrli produced no numeric output: {completed.stdout!r}")

        return float(values[-1])

    @staticmethod
    def _is_float(token: str) -> bool:
        try:
            float(token)
        except ValueError:
            return False

        return True


def find_zimtohrli() -> Optional[Path]:
    """Path of the `zimtohrli` binary on the system, when installed."""
    binary = shutil.which(ZIMTOHRLI_BINARY)
    return Path(binary) if binary else None
