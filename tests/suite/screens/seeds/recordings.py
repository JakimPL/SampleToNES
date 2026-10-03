from dataclasses import dataclass
from pathlib import Path
from typing import Final

import numpy as np
import soundfile

from sampletones_core.compatibility.kind import ObjectKind
from tests.suite.compatibility import ARCHIVED_VERSIONS, archived, stored_document

RECORDING_SAMPLE_RATE: Final[int] = 44100
RECORDING_AMPLITUDE: Final[float] = 0.5
STORED_RECORDING_SECONDS: Final[float] = 0.5
STORED_RECORDING_FREQUENCY: Final[float] = 220.0
AUDIO_PATH_FIELD: Final[str] = "audio_filepath"


@dataclass(frozen=True)
class Recording:
    """A recording in the home: a sine tone of ``frequency`` hertz lasting ``seconds``."""

    destination: Path
    seconds: float
    frequency: float

    def write(self) -> None:
        """Writes the sine tone to the destination as a sound file."""
        self.destination.parent.mkdir(parents=True, exist_ok=True)
        times = np.arange(round(self.seconds * RECORDING_SAMPLE_RATE)) / RECORDING_SAMPLE_RATE
        tone = RECORDING_AMPLITUDE * np.sin(2.0 * np.pi * self.frequency * times)
        soundfile.write(self.destination, tone, RECORDING_SAMPLE_RATE)


def stored_recording() -> Recording:
    """The recording the archived reconstruction names, laid where its relative path leads from the home.

    The application runs in the home, so a relative path the document names resolves there.
    """
    document = stored_document(archived(ObjectKind.RECONSTRUCTION, ARCHIVED_VERSIONS[ObjectKind.RECONSTRUCTION]))
    return Recording(
        destination=Path.cwd() / document[AUDIO_PATH_FIELD],
        seconds=STORED_RECORDING_SECONDS,
        frequency=STORED_RECORDING_FREQUENCY,
    )
