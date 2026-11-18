import sys
from argparse import ArgumentParser
from contextlib import chdir
from pathlib import Path
from typing import Final, Sequence

import soundfile

from assets.footage.document import located_document
from assets.footage.mastering import mastered, require_ffmpeg
from assets.footage.paths import DEMO_SPECIFICATION, FOOTAGE_DIRECTORY, SOUNDTRACK_FILE
from assets.footage.schedule import schedule
from assets.footage.soundtrack import ListeningAudio, soundtrack
from assets.footage.specification import Footage
from sampletones_application.logic.reconstruction.data import ReconstructionData

PROGRAM: Final[str] = "python -m assets.footage"
DESCRIPTION: Final[str] = "film the Reconstructions tab walking through a timeline of listenings"
SOUNDTRACK_SUBTYPE: Final[str] = "PCM_24"


def main(argv: Sequence[str]) -> int:
    """Masters the footage's soundtrack from its specification and writes it under the footage's build folder."""
    parser = ArgumentParser(prog=PROGRAM, description=DESCRIPTION)
    parser.add_argument("--spec", type=Path, default=DEMO_SPECIFICATION, help="the footage specification (YAML)")
    arguments = parser.parse_args(list(argv))
    require_ffmpeg()

    specification = arguments.spec.resolve()
    footage = Footage.load(specification)
    document = located_document(footage, specification)
    with chdir(document.working_directory):
        data = ReconstructionData.load(document.path)

    config = data.reconstruction.config
    timeline_schedule = schedule(
        footage.timeline,
        tick_rate=config.library.nes_frequency,
        frame_rate=footage.frame_rate,
    )
    sound = soundtrack(
        ListeningAudio(data),
        timeline_schedule,
        frame_length=config.frame_length,
        sample_rate=config.sample_rate,
    )
    folder = FOOTAGE_DIRECTORY / specification.stem
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / SOUNDTRACK_FILE
    soundfile.write(target, mastered(sound, config.sample_rate), config.sample_rate, subtype=SOUNDTRACK_SUBTYPE)
    print(f"Wrote {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
