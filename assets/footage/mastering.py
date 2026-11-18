import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Final, List

import numpy as np
import soundfile

from sampletones_shared.utils.system.programs import locate_program
from sampletones_tools.ffmpeg import FFMPEG, missing_ffmpeg_message

PURPOSE: Final[str] = "footage is mastered and encoded with it"
TARGET_LOUDNESS: Final[float] = -14.0
TRUE_PEAK_CEILING: Final[float] = -1.0
LIMITER_CEILING: Final[float] = -2.0
LIMITER_ATTACK_MILLISECONDS: Final[float] = 1.0
LIMITER_RELEASE_MILLISECONDS: Final[float] = 60.0
MASTERING_PASSES: Final[int] = 2
WORKING_SUBTYPE: Final[str] = "FLOAT"
SUMMARY: Final[str] = "Summary:"
INTEGRATED_PATTERN: Final[re.Pattern[str]] = re.compile(r"I:\s+(-?[\d.]+|-inf) LUFS")
PEAK_PATTERN: Final[re.Pattern[str]] = re.compile(r"Peak:\s+(-?[\d.]+|-inf) dBFS")
UNATTENDED: Final[List[str]] = ["-nostdin", "-nostats", "-y"]


class MissingFfmpegError(RuntimeError):
    """Raised when ffmpeg, which masters and encodes the footage, is absent."""


class LoudnessReadingError(RuntimeError):
    """Raised when ffmpeg's loudness meter prints no summary to read."""


@dataclass(frozen=True)
class Loudness:
    """A sound's integrated loudness in LUFS and its true peak in dBTP, as the EBU R128 meter reads them."""

    integrated: float
    true_peak: float


def require_ffmpeg() -> None:
    """Raises:
    MissingFfmpegError: If ffmpeg is absent, naming how this system installs it.
    """
    if locate_program(FFMPEG) is None:
        raise MissingFfmpegError(missing_ffmpeg_message(PURPOSE))


def decibel_gain(decibels: float) -> float:
    return float(10.0 ** (decibels / 20.0))


def loudness_command(source: Path) -> List[str]:
    return [FFMPEG, *UNATTENDED, "-i", str(source), "-af", "ebur128=peak=true", "-f", "null", "-"]


def limiter_command(source: Path, target: Path, *, gain_decibels: float) -> List[str]:
    """Raises ``source`` by ``gain_decibels`` and holds its peaks under the limiter's ceiling, into ``target``."""
    limiter = (
        f"alimiter=limit={decibel_gain(LIMITER_CEILING):.6f}:attack={LIMITER_ATTACK_MILLISECONDS}"
        f":release={LIMITER_RELEASE_MILLISECONDS}:level=disabled"
    )
    return [
        FFMPEG,
        *UNATTENDED,
        "-loglevel",
        "error",
        "-i",
        str(source),
        "-af",
        f"volume={gain_decibels:.6f}dB,{limiter}",
        "-c:a",
        "pcm_f32le",
        str(target),
    ]


def parse_loudness(report: str) -> Loudness:
    """The loudness the meter's closing summary states.

    Raises:
        LoudnessReadingError: If the report holds no summary with both readings.
    """
    summary = report[report.rfind(SUMMARY) :] if SUMMARY in report else ""
    integrated = INTEGRATED_PATTERN.search(summary)
    peak = PEAK_PATTERN.search(summary)
    if integrated is None or peak is None:
        raise LoudnessReadingError(f"ffmpeg printed no loudness summary:\n{report[-2000:]}")

    return Loudness(integrated=float(integrated.group(1)), true_peak=float(peak.group(1)))


def measure(audio: np.ndarray, sample_rate: int) -> Loudness:
    """The loudness of ``audio`` as ffmpeg's EBU R128 meter reads it."""
    with tempfile.TemporaryDirectory() as folder:
        source = Path(folder) / "measured.wav"
        soundfile.write(source, audio, sample_rate, subtype=WORKING_SUBTYPE)
        report = subprocess.run(
            loudness_command(source), stdin=subprocess.DEVNULL, capture_output=True, text=True, check=True
        )

    return parse_loudness(report.stderr)


def mastered(audio: np.ndarray, sample_rate: int) -> np.ndarray:
    """``audio`` brought to the target loudness, its peaks held by the limiter and its true peak under the
    ceiling.

    Each pass measures what the last one left and raises it to the target, so the limiting a pass applies
    is made up for by the next.
    """
    result = audio
    with tempfile.TemporaryDirectory() as folder:
        source, target = Path(folder) / "source.wav", Path(folder) / "limited.wav"
        for _ in range(MASTERING_PASSES):
            loudness = measure(result, sample_rate)
            soundfile.write(source, result, sample_rate, subtype=WORKING_SUBTYPE)
            command = limiter_command(source, target, gain_decibels=TARGET_LOUDNESS - loudness.integrated)
            subprocess.run(command, stdin=subprocess.DEVNULL, check=True)
            result, _ = soundfile.read(target, dtype="float64")

    true_peak = measure(result, sample_rate).true_peak
    if true_peak > TRUE_PEAK_CEILING:
        result = result * decibel_gain(TRUE_PEAK_CEILING - true_peak)

    return result
