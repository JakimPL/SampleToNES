import subprocess
from pathlib import Path
from typing import Final, List

from assets.footage.frames import FRAME_PATTERN
from sampletones_tools.ffmpeg import FFMPEG, UNATTENDED

VIDEO_CODEC: Final[str] = "libx264"
PRESET: Final[str] = "slow"
QUALITY: Final[int] = 14
PIXEL_FORMAT: Final[str] = "yuv420p"
COLORS: Final[str] = "bt709"
RANGE: Final[str] = "tv"
AUDIO_CODEC: Final[str] = "aac"
AUDIO_BITRATE: Final[str] = "256k"
AUDIO_RATE: Final[int] = 48000
AUDIO_CHANNELS: Final[int] = 2
FAST_START: Final[str] = "+faststart"


def encode_command(frames: Path, soundtrack: Path, target: Path, *, frame_rate: int) -> List[str]:
    """Encodes the numbered frames in ``frames`` at ``frame_rate`` with ``soundtrack`` into the video ``target``.

    The frames are converted with the BT.709 matrix the video is tagged with, so players show the colors the
    screen drew, and the mono soundtrack plays on both channels at the rate the platforms take.
    """
    return [
        FFMPEG,
        *UNATTENDED,
        "-loglevel",
        "error",
        "-framerate",
        str(frame_rate),
        "-i",
        str(frames / FRAME_PATTERN),
        "-i",
        str(soundtrack),
        "-map",
        "0:v",
        "-map",
        "1:a",
        "-vf",
        f"scale=out_color_matrix={COLORS}:out_range={RANGE}",
        "-c:v",
        VIDEO_CODEC,
        "-preset",
        PRESET,
        "-crf",
        str(QUALITY),
        "-pix_fmt",
        PIXEL_FORMAT,
        "-colorspace",
        COLORS,
        "-color_primaries",
        COLORS,
        "-color_trc",
        COLORS,
        "-color_range",
        RANGE,
        "-c:a",
        AUDIO_CODEC,
        "-b:a",
        AUDIO_BITRATE,
        "-ar",
        str(AUDIO_RATE),
        "-ac",
        str(AUDIO_CHANNELS),
        "-movflags",
        FAST_START,
        "-shortest",
        str(target),
    ]


def encode(frames: Path, soundtrack: Path, target: Path, *, frame_rate: int) -> None:
    """Encodes the frames in ``frames`` and ``soundtrack`` into the video ``target``, making its folder on the way."""
    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        encode_command(frames, soundtrack, target, frame_rate=frame_rate),
        stdin=subprocess.DEVNULL,
        check=True,
    )
