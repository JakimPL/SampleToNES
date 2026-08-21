#!/usr/bin/env python3

import argparse
import struct
import subprocess
import sys
from pathlib import Path
from typing import Dict, Final, List, Sequence

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
from sampletones_shared.paths.extensions import EXT_FILE_NSF, EXT_FILE_WAVE
from sampletones_shared.utils.system.programs import (
    locate_program,
    missing_program_message,
)
from sampletones_shared.utils.system.system import System

SAMPLES_DIRECTORY: Final[Path] = Path("build") / "nsf"
TAIL_SECONDS: Final[float] = 0.5
FFMPEG: Final[str] = "ffmpeg"
GME_FORMAT: Final[str] = "libgme"
WORD: Final[str] = "<H"
RENDER_PURPOSE: Final[str] = f"an exported file is decoded through its {GME_FORMAT} demuxer"

INSTALL_HINTS: Final[Dict[System, str]] = {
    System.LINUX: "sudo apt install ffmpeg",
    System.MACOS: "brew install ffmpeg",
    System.WINDOWS: "install ffmpeg from https://ffmpeg.org and add its bin directory to PATH",
}


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


def main(argv: Sequence[str]) -> int:
    """Renders every exported file in a directory to a wave beside it."""

    parser = argparse.ArgumentParser(
        description="Render exported .nsf files to waves with ffmpeg's libgme demuxer.",
    )
    parser.add_argument(
        "--directory",
        type=Path,
        default=SAMPLES_DIRECTORY,
        help="directory holding the exported .nsf files",
    )
    parser.add_argument(
        "--tail",
        type=float,
        default=TAIL_SECONDS,
        help="seconds to keep past the end of each song",
    )
    arguments = parser.parse_args(list(argv))

    if locate_program(FFMPEG) is None:
        print(missing_program_message(FFMPEG, RENDER_PURPOSE, INSTALL_HINTS), file=sys.stderr)
        return 1

    if not decodes_exports():
        print(
            f"{FFMPEG} reports no {GME_FORMAT} demuxer; rendering needs a build made with --enable-libgme",
            file=sys.stderr,
        )
        return 1

    sources: List[Path] = sorted(arguments.directory.glob(f"*{EXT_FILE_NSF}"))
    if not sources:
        print(
            f"no {EXT_FILE_NSF} files in {arguments.directory}; run make nsf-samples first",
            file=sys.stderr,
        )
        return 1

    code_length = len(DriverImage.load().code)
    for source in sources:
        destination = source.with_suffix(EXT_FILE_WAVE)
        seconds = song_seconds(source.read_bytes(), code_length) + arguments.tail
        try:
            render(source, destination, seconds)
        except subprocess.CalledProcessError as error:
            print(
                f"{FFMPEG} rejected {source}: exit status {error.returncode}",
                file=sys.stderr,
            )
            return 1

        print(f"{destination}  {seconds:.3f} s")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
