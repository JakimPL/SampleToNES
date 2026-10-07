from pathlib import Path
from typing import Final, List

from pydantic import ValidationError

from sampletones_shared.constants.nes import PAL_FREQUENCY
from sampletones_shared.paths.user import RECONSTRUCTIONS_DIRECTORY
from tests.suite.screens.worlds.songs import BASS_VOICE, LINE, PAD

UNSOUND_RECONSTRUCTION: Final[Path] = RECONSTRUCTIONS_DIRECTORY / "Unsound.stn"
UNSOUND_AT_OTHER_RATE: Final[Path] = RECONSTRUCTIONS_DIRECTORY / "Unsound PAL.stn"
SOUND_AT_OTHER_RATE: Final[Path] = RECONSTRUCTIONS_DIRECTORY / "Sound PAL.stn"
OTHER_RATE: Final[int] = PAL_FREQUENCY
UNSOUND_FAILURE: Final[str] = ValidationError.__name__
ADD_TO_SEQUENCER: Final[str] = "global.context.label.add_to_sequencer"
ADD_SAMPLE_FROM_FILE: Final[str] = "sequencer.voices.label.add_sample"
REPLACE_SAMPLE: Final[str] = "global.context.template.replace_sample"
LINE_POSITION: Final[str] = "00"
SAMPLE_KEY: Final[str] = "sample"
PROJECT_TITLE_PART: Final[int] = 1
PLACEHOLDER_START: Final[str] = "{"
FREQUENCY_MISMATCH: Final[str] = "global.dialog.message.frequency_mismatch"
SILENT_FAILURE_BUG: Final[str] = "bugs-and-todos § Bugs: A failure no coordinator catches is logged with no message"
HALF_DONE_GESTURE_BUG: Final[str] = "bugs-and-todos § Bugs: A gesture failing midway keeps what landed before it"
ATTEMPTS: Final[int] = 2
ARRANGED_VOICES: Final[List[str]] = [LINE, BASS_VOICE, PAD]
