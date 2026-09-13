import argparse
import platform as running
import shutil
import subprocess
import sys
from typing import Final, Sequence

from bootstrap.platforms.factory import current_platform

HOMEBREW: Final[str] = "brew"
PORTAUDIO: Final[str] = "portaudio"


def portaudio_prefix() -> str:
    """Where Homebrew installed PortAudio, or empty where Homebrew is absent."""
    if shutil.which(HOMEBREW) is None:
        return ""

    completed = subprocess.run(
        [HOMEBREW, "--prefix", PORTAUDIO],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return ""

    return completed.stdout.strip()


def main(argv: Sequence[str]) -> int:
    """Prints the variables a build exports so audio playback compiles, one ``KEY=VALUE`` per line."""
    parser = argparse.ArgumentParser(description="Print the build environment audio playback compiles under.")
    parser.parse_args(list(argv))

    lines = current_platform().build_environment(
        machine=running.machine(),
        portaudio_prefix=portaudio_prefix(),
    )
    for line in lines:
        print(line)

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
