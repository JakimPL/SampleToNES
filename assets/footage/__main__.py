import os
import sys
import threading
from argparse import ArgumentParser
from contextlib import chdir, contextmanager
from pathlib import Path
from typing import Dict, Final, Iterator, Sequence

import pytest
import soundfile
from tqdm import tqdm

from assets.footage.document import located_document, stem_ids
from assets.footage.encoding import encode
from assets.footage.frames import filmed, prepare_frames
from assets.footage.mastering import mastered, require_ffmpeg
from assets.footage.paths import (
    DEMO_SPECIFICATION,
    FOOTAGE_DIRECTORY,
    FRAMES_FOLDER,
    KEPT_DIRECTORY,
    SCENES_DIRECTORY,
    SOUNDTRACK_FILE,
    VIDEO_SUFFIX,
)
from assets.footage.schedule import Schedule, schedule
from assets.footage.shoot import Shoot, Take, digest, take_environment
from assets.footage.shot import SCREEN
from assets.footage.soundtrack import ListeningAudio, soundtrack
from assets.footage.specification import Footage
from assets.stage.paths import HOMES_DIRECTORY
from assets.stage.runner import pytest_arguments, run_environment
from sampletones_application.logic.reconstruction.data import ReconstructionData
from sampletones_shared.paths.source import REPOSITORY_ROOT

PROGRAM: Final[str] = "python -m assets.footage"
DESCRIPTION: Final[str] = "film the Reconstructions tab walking through a timeline of listenings"
SOUNDTRACK_SUBTYPE: Final[str] = "PCM_24"
NAMING: Final[Dict[str, str]] = {
    "python_files": "*_footage.py",
    "python_classes": "*Footage",
    "python_functions": "footage_*",
}
PROGRESS_SECONDS: Final[float] = 1.0
PROGRESS_UNIT: Final[str] = "frame"


class UnfinishedFootageError(RuntimeError):
    """Raised when the filming scene stopped short of the frames the take asked for."""


def main(argv: Sequence[str]) -> int:
    """Masters the footage's soundtrack, films the frames still missing and encodes them with it into a video.

    Every frame is kept as it is filmed, so a run cut short resumes where it stopped, and the frames are
    filmed again once the specification or the document changes.
    """
    parser = ArgumentParser(prog=PROGRAM, description=DESCRIPTION)
    parser.add_argument("--spec", type=Path, default=DEMO_SPECIFICATION, help="the footage specification (YAML)")
    parser.add_argument("-o", "--output", type=Path, default=None, help="the video written (MP4)")
    parser.add_argument("--limit", type=int, default=None, help="film this many frames at most; 0 films none")
    parser.add_argument("--fresh", action="store_true", help="film every frame again")
    arguments = parser.parse_args(list(argv))
    require_ffmpeg()

    specification = arguments.spec.resolve()
    footage = Footage.load(specification)
    folder = FOOTAGE_DIRECTORY / specification.stem
    print(f"Reading {specification.name}")
    document = located_document(footage, specification)
    with chdir(document.working_directory):
        data = ReconstructionData.load(document.path)

    config = data.reconstruction.config
    laid = schedule(footage.timeline, tick_rate=config.library.nes_frequency, frame_rate=footage.frame_rate)
    sound = folder / SOUNDTRACK_FILE
    print(f"Mastering {sound}")
    write_soundtrack(data, laid, sound)

    shoot = Shoot(
        document=None if footage.document is None else document.path,
        digest=digest(document.path),
        tick_length=config.frame_length,
        stem_keys={name: str(stem_id) for name, stem_id in stem_ids(data.reconstruction.stems_data).items()},
        schedule=laid,
    )
    frames = folder / FRAMES_FOLDER
    prepare_frames(frames, shoot.model_dump_json(), fresh=arguments.fresh)
    stop = laid.frame_count if arguments.limit is None else min(arguments.limit, laid.frame_count)
    if stop == 0:
        return 0

    status = film(Take(shoot=shoot, frames=frames, stop=stop))
    if status != 0:
        return status
    if filmed(frames) < stop:
        raise UnfinishedFootageError(f"The scene filmed {filmed(frames)} of {stop} frames into {frames}")

    target = arguments.output or folder / f"{specification.stem}{VIDEO_SUFFIX}"
    print(f"Encoding {stop} frames")
    encode(frames, sound, target, frame_rate=footage.frame_rate)
    print(f"Wrote {target}")
    return 0


def write_soundtrack(data: ReconstructionData, laid: Schedule, target: Path) -> None:
    """Writes the mastered soundtrack of the schedule ``laid`` over the document ``data`` to ``target``."""
    config = data.reconstruction.config
    sound = soundtrack(ListeningAudio(data), laid, frame_length=config.frame_length, sample_rate=config.sample_rate)
    target.parent.mkdir(parents=True, exist_ok=True)
    soundfile.write(target, mastered(sound, config.sample_rate), config.sample_rate, subtype=SOUNDTRACK_SUBTYPE)


def film(take: Take) -> int:
    """Runs the filming scene for the frames of ``take`` still missing and returns pytest's exit status."""
    done = filmed(take.frames)
    if done >= take.stop:
        return 0

    print(f"Filming frames {done} to {take.stop}")
    HOMES_DIRECTORY.mkdir(parents=True, exist_ok=True)
    os.environ.update(
        run_environment(
            dict(os.environ),
            screen=SCREEN,
            kept=KEPT_DIRECTORY,
            homes=HOMES_DIRECTORY,
            repository=REPOSITORY_ROOT,
        )
    )
    os.environ.update(take_environment(take))
    arguments = pytest_arguments(SCENES_DIRECTORY, NAMING, markers={}, workers=None, selection=None)
    with progress(take.frames, done=done, total=take.stop):
        return int(pytest.main(arguments))


@contextmanager
def progress(frames: Path, *, done: int, total: int) -> Iterator[None]:
    """Shows a bar of the frames kept in ``frames`` while the scene films them in a process of its own."""
    finished = threading.Event()

    def watch() -> None:
        with tqdm(total=total, initial=done, unit=PROGRESS_UNIT) as bar:
            while not finished.wait(PROGRESS_SECONDS):
                bar.update(filmed(frames) - bar.n)
            bar.update(filmed(frames) - bar.n)

    watcher = threading.Thread(target=watch, daemon=True)
    watcher.start()
    try:
        yield
    finally:
        finished.set()
        watcher.join()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
