import os
from pathlib import Path
from typing import Final, Tuple

EXT_FILE_JSON: Final[str] = ".json"
EXT_FILE_YAML: Final[str] = ".yaml"
EXT_FILE_LIBRARY: Final[str] = ".ins"
EXT_FILE_INSTRUMENT: Final[str] = ".fti"
EXT_FILE_RECONSTRUCTION: Final[str] = ".stn"
EXT_FILE_PROJECT: Final[str] = ".stp"
EXT_FILE_MODULE: Final[str] = ".ftm"
EXT_FILE_BITPHASE: Final[str] = ".btp"
EXT_FILE_NSF: Final[str] = ".nsf"
EXT_FILE_LOG: Final[str] = ".log"
EXT_FILE_WINDOWS_PROGRAM: Final[str] = ".exe"
EXT_FILE_WAVE: Final[str] = ".wav"
EXT_FILE_MP3: Final[str] = ".mp3"
EXT_FILE_FLAC: Final[str] = ".flac"
EXT_FILE_OGG: Final[str] = ".ogg"
EXT_FILE_AIFF: Final[str] = ".aiff"
EXT_FILE_AU: Final[str] = ".au"
EXT_FILES_AUDIO: Final[Tuple[str, ...]] = (
    EXT_FILE_WAVE,
    EXT_FILE_MP3,
    EXT_FILE_FLAC,
    EXT_FILE_OGG,
    EXT_FILE_AIFF,
    EXT_FILE_AU,
)


def is_audio_file(path: Path, extensions: Tuple[str, ...] = EXT_FILES_AUDIO) -> bool:
    """Whether a path names a recording a run converts.

    A recording is a file the reader may inspect, so an entry of a folder that lists its names and
    keeps the rest to itself reads as none. ``os.path.isfile`` answers False for such an entry,
    where ``Path.is_file`` raises ``PermissionError``, so a walk goes on past it.
    """
    return path.suffix.lower() in extensions and os.path.isfile(path)
