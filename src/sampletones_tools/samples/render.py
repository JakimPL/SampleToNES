import struct
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Final, List

from sampletones_player.driver.image import DriverImage
from sampletones_player.specification.clock import (
    FIXED_POINT_SCALE,
    NTSC_FRAME_RATE,
)
from sampletones_player.specification.nsf import HEADER_SIZE
from sampletones_player.specification.song import (
    STEP_FRACTION_OFFSET,
    STEP_WHOLE_OFFSET,
    TOTAL_TICKS_OFFSET,
)
from sampletones_shared.exceptions import SampleToNESError
from sampletones_shared.paths.extensions import EXT_FILE_NSF, EXT_FILE_WAVE
from sampletones_shared.utils.system.programs import (
    locate_program,
    missing_program_message,
)
from sampletones_shared.utils.system.system import System

FFMPEG: Final[str] = "ffmpeg"
GME_FORMAT: Final[str] = "libgme"
WORD: Final[str] = "<H"
RENDER_PURPOSE: Final[str] = f"an exported file is decoded through its {GME_FORMAT} demuxer"

INSTALL_HINTS: Final[Dict[System, str]] = {
    System.LINUX: "sudo apt install ffmpeg",
    System.MACOS: "brew install ffmpeg",
    System.WINDOWS: "install ffmpeg from https://ffmpeg.org and add its bin directory to PATH",
}


class RenderingError(SampleToNESError):
    """Rendering stopped: ffmpeg is absent or carries no libgme demuxer, or a file was rejected."""


@dataclass(frozen=True)
class RenderedWave:
    """One exported file rendered to a wave beside it.

    Attributes:
        source: The `.nsf` file played.
        destination: The wave written.
        seconds: How much of the song the wave holds, the tail included.
    """

    source: Path
    destination: Path
    seconds: float


def decodes_exports() -> bool:
    """Whether the installed ffmpeg carries the demuxer an exported file is read through.

    A demuxer is a build option, so ffmpeg is asked which ones it carries rather than taken to
    carry this one.

    Returns:
        bool: True where ffmpeg reports the libgme demuxer among its own.

    Raises:
        CalledProcessError: If ffmpeg fails to report its demuxers.
    """
    reported = subprocess.run(
        [FFMPEG, "-hide_banner", "-loglevel", "error", "-demuxers"],
        capture_output=True,
        text=True,
        check=True,
    )
    return GME_FORMAT in reported.stdout


def require_renderer() -> None:
    """Holds a render to an ffmpeg that decodes exported files.

    Raises:
        RenderingError: If ffmpeg is absent, naming how this system installs it, or carries no
            libgme demuxer.
    """
    if locate_program(FFMPEG) is None:
        raise RenderingError(missing_program_message(FFMPEG, RENDER_PURPOSE, INSTALL_HINTS))

    if not decodes_exports():
        raise RenderingError(
            f"{FFMPEG} reports no {GME_FORMAT} demuxer; rendering needs a build made with --enable-libgme"
        )


def song_seconds(data: bytes, code_length: int) -> float:
    """How long the song in an exported file lasts, read out of the block behind the driver.

    The block states the ticks the song covers and the step the driver advances them by, which
    gives the play calls the song takes, and the console makes one of those every video frame.

    Args:
        data: The whole `.nsf` file, header included.
        code_length: The length of the driver the file carries.

    Returns:
        float: The seconds the song lasts.
    """
    block = data[HEADER_SIZE + code_length :]
    ticks: int = struct.unpack_from(WORD, block, TOTAL_TICKS_OFFSET)[0]
    fraction: int = struct.unpack_from(WORD, block, STEP_FRACTION_OFFSET)[0]
    step: float = block[STEP_WHOLE_OFFSET] + fraction / FIXED_POINT_SCALE
    play_calls = ticks / step
    return play_calls / float(NTSC_FRAME_RATE)


def render(source: Path, destination: Path, seconds: float) -> None:
    """Decodes one exported file to a wave through libgme's own 2A03.

    Args:
        source: The `.nsf` file to play.
        destination: Where the rendered wave is written.
        seconds: How much of the song to render.

    Raises:
        CalledProcessError: If ffmpeg rejects the file.
    """
    subprocess.run(
        [
            FFMPEG,
            "-y",
            "-loglevel",
            "error",
            "-f",
            GME_FORMAT,
            "-i",
            str(source),
            "-t",
            f"{seconds:.3f}",
            str(destination),
        ],
        check=True,
    )


def render_directory(directory: Path, tail_seconds: float) -> List[RenderedWave]:
    """Renders every exported file in a directory to a wave beside it.

    Args:
        directory: The directory holding the `.nsf` files.
        tail_seconds: How much to keep past the end of each song.

    Returns:
        List[RenderedWave]: The waves written, in path order.

    Raises:
        RenderingError: If ffmpeg is unusable, the directory holds no exported file, or ffmpeg
            rejects one.
    """
    require_renderer()
    sources = sorted(directory.glob(f"*{EXT_FILE_NSF}"))
    if not sources:
        raise RenderingError(f"no {EXT_FILE_NSF} files in {directory}")

    code_length = len(DriverImage.load().code)
    rendered: List[RenderedWave] = []
    for source in sources:
        destination = source.with_suffix(EXT_FILE_WAVE)
        seconds = song_seconds(source.read_bytes(), code_length) + tail_seconds
        try:
            render(source, destination, seconds)
        except subprocess.CalledProcessError as error:
            raise RenderingError(f"{FFMPEG} rejected {source}: exit status {error.returncode}") from error

        rendered.append(RenderedWave(source=source, destination=destination, seconds=seconds))

    return rendered
