from typing import Final, Tuple

RUN_TIMEOUT_SECONDS: Final[float] = 120.0
BASS: Final[str] = "bass.wav"
LEAD: Final[str] = "lead.wav"
DRUMS: Final[str] = "drums.wav"
ALBUM: Final[str] = "Album"
DISC: Final[str] = "Disc2"
ALBUM_TAKES: Final[Tuple[str, ...]] = ("one.wav", "two.wav")
DISC_TAKES: Final[Tuple[str, ...]] = ("three.wav",)
RECONSTRUCTION_SUFFIX: Final[str] = ".stn"
