"""Writes the archived corpus using the API of the v0.3.1 tree, which is the release it belongs to.

This is the backward port of ``sampletones_tools/compatibility/documents.py`` and ``writer.py``.
It runs inside a worktree at the tag, never from the current tree, and nothing imports it: it is
kept beside the files it wrote so a reader can see exactly how each of them was produced.

    git worktree add <scratch>/v0.3.1 v0.3.1
    cd <scratch>/v0.3.1 && uv sync --frozen
    cp <checkout>/tests/data/compatibility/generators/v0_3_1.py .
    uv run python v0_3_1.py --output <checkout>/tests/data/compatibility
    cd <checkout> && git worktree remove --force <scratch>/v0.3.1
"""

import argparse
from pathlib import Path
from typing import Dict, Final, List, Tuple

import numpy as np

from sampletones_core.configs import Config
from sampletones_core.constants.enums import GeneratorName, SpectrumMethod
from sampletones_core.fft import Window
from sampletones_core.fft.features import get_feature_extractor
from sampletones_core.generators import PulseGenerator
from sampletones_core.instructions import (
    InstructionUnion,
    NoiseInstruction,
    PulseInstruction,
    TriangleInstruction,
)
from sampletones_core.library import InstructionLibraryFragment
from sampletones_core.library.data import InstructionLibraryData
from sampletones_core.project.container import ProjectContainer
from sampletones_core.project.instruments.instrument import Instrument
from sampletones_core.project.instruments.note_off import NoteOff
from sampletones_core.project.instruments.sample import Sample
from sampletones_core.project.patterns.pattern import Pattern
from sampletones_core.project.patterns.row import Row
from sampletones_core.project.project import Project
from sampletones_core.project.settings import ProjectSettings
from sampletones_core.reconstructions import Reconstruction

SOURCE_PATH: Final[Path] = Path("samples") / "kick.wav"
COEFFICIENT: Final[float] = 0.75
ROWS_PER_PATTERN: Final[int] = 4
PATTERN_NAME: Final[str] = "verse"
FIRST_SAMPLE_NAME: Final[str] = "kick"
SECOND_SAMPLE_NAME: Final[str] = "kick again"
PROJECT_TITLE: Final[str] = "Corpus"
PROJECT_AUTHOR: Final[str] = "Archivist"
PROJECT_COMMENT: Final[str] = "A document kept to be read back"
PROJECT_TEMPO: Final[int] = 132
ROW_TRANSPOSE: Final[int] = 3
ROW_VOLUME: Final[int] = 9
LIBRARY_SAMPLE_RATE: Final[int] = 11025
LIBRARY_GAMMA: Final[int] = 50
EMBEDDED_GENERATOR: Final[GeneratorName] = GeneratorName.PULSE2
APPROXIMATION_SAMPLES: Final[int] = 8
STORED_DRIVE: Final[float] = 1.5


def corpus_instructions() -> Dict[GeneratorName, List[InstructionUnion]]:
    """Three frames on every channel: one sounding, one silent, one sounding."""
    return {
        GeneratorName.PULSE1: [
            PulseInstruction(on=True, pitch=45, volume=11, duty_cycle=2),
            PulseInstruction(on=False, pitch=45, volume=0, duty_cycle=0),
            PulseInstruction(on=True, pitch=48, volume=7, duty_cycle=1),
        ],
        GeneratorName.PULSE2: [
            PulseInstruction(on=True, pitch=52, volume=9, duty_cycle=0),
            PulseInstruction(on=False, pitch=52, volume=0, duty_cycle=0),
            PulseInstruction(on=True, pitch=52, volume=9, duty_cycle=3),
        ],
        GeneratorName.TRIANGLE: [
            TriangleInstruction(on=True, pitch=33),
            TriangleInstruction(on=False, pitch=33),
            TriangleInstruction(on=True, pitch=35),
        ],
        GeneratorName.NOISE: [
            NoiseInstruction(on=True, period=5, volume=6, short=False),
            NoiseInstruction(on=False, period=5, volume=0, short=False),
            NoiseInstruction(on=True, period=9, volume=12, short=True),
        ],
    }


def _audio() -> np.ndarray:
    """A few samples standing for the rendered audio a 2.1 file carried beside its instructions."""
    return np.linspace(-0.5, 0.5, APPROXIMATION_SAMPLES, dtype=np.float32)


def _reconstruction_config(generators: List[GeneratorName]) -> Config:
    """The configuration a 2.1 run recorded: the channels it handed out, and how hard it drove them."""
    base = Config()
    generation = base.generation.model_copy(update={"generators": generators, "drive": STORED_DRIVE})
    return base.model_copy(update={"generation": generation})


def corpus_reconstruction() -> Reconstruction:
    """A reconstruction naming every channel and the recording it was built from."""
    instructions = corpus_instructions()
    generators = list(instructions)
    return Reconstruction.create(
        approximation=_audio(),
        approximations={generator_name: _audio() for generator_name in generators},
        instructions=instructions,
        config=_reconstruction_config(generators),
        coefficient=COEFFICIENT,
        audio_filepath=SOURCE_PATH,
    )


def embedded_reconstruction() -> Reconstruction:
    """The reconstruction a project carries, sounding one channel while the rest stand by."""
    instructions: Dict[GeneratorName, List[InstructionUnion]] = {
        EMBEDDED_GENERATOR: [
            PulseInstruction(on=True, pitch=40, volume=15, duty_cycle=1),
            PulseInstruction(on=False, pitch=40, volume=0, duty_cycle=0),
        ]
    }
    return Reconstruction.create(
        approximation=_audio(),
        approximations={EMBEDDED_GENERATOR: _audio()},
        instructions=instructions,
        config=_reconstruction_config([EMBEDDED_GENERATOR]),
        coefficient=COEFFICIENT,
        audio_filepath=SOURCE_PATH,
    )


def library_config() -> Config:
    """The configuration the archived library is analyzed under."""
    base = Config()
    library = base.library.model_copy(
        update={
            "spectrum_method": SpectrumMethod.FFT,
            "transformation_gamma": LIBRARY_GAMMA,
            "sample_rate": LIBRARY_SAMPLE_RATE,
        }
    )
    return base.model_copy(update={"library": library})


def library_tones() -> Tuple[PulseInstruction, ...]:
    """The tones the archived library holds, each measured and stored."""
    return (
        PulseInstruction(on=True, pitch=57, volume=12, duty_cycle=2),
        PulseInstruction(on=True, pitch=45, volume=8, duty_cycle=1),
    )


def corpus_library() -> InstructionLibraryData:
    """A library holding a couple of measured tones, small enough to keep."""
    config = library_config()
    extractor = get_feature_extractor(config, Window.from_config(config))
    generator = PulseGenerator(config, GeneratorName.PULSE1)
    fragments = {
        instruction: InstructionLibraryFragment.create(generator, instruction, extractor)
        for instruction in library_tones()
    }
    return InstructionLibraryData.create(config, fragments)


def corpus_project(reconstruction: Reconstruction) -> Project:
    """A project arranging one reconstruction under two samples."""
    settings = ProjectSettings(tempo=PROJECT_TEMPO)
    project = Project.create(
        title=PROJECT_TITLE,
        author=PROJECT_AUTHOR,
        comment=PROJECT_COMMENT,
        rows_per_pattern=ROWS_PER_PATTERN,
        settings=settings,
    )
    first = Sample(name=FIRST_SAMPLE_NAME, reconstruction=reconstruction)
    second = Sample(name=SECOND_SAMPLE_NAME, reconstruction=reconstruction)
    project.samples.append(first)
    project.samples.append(second)
    project.song.channels[EMBEDDED_GENERATOR].patterns[0] = Pattern(
        name=PATTERN_NAME,
        rows=[
            Row(command=Instrument(sample_id=first.id, generator_name=EMBEDDED_GENERATOR)),
            Row(
                command=Instrument(sample_id=second.id, generator_name=EMBEDDED_GENERATOR),
                transpose=ROW_TRANSPOSE,
                volume=ROW_VOLUME,
            ),
            Row(command=NoteOff()),
            Row(),
        ],
    )
    return project


def main() -> None:
    parser = argparse.ArgumentParser(description="write the v0.3.1 compatibility corpus")
    parser.add_argument("--output", required=True, help="the corpus directory the files land in")
    arguments = parser.parse_args()
    root = Path(arguments.output)

    for kind, name in (("reconstruction", "v2_1.stn"), ("library", "v2_0.ins"), ("project", "v1_0.stp")):
        (root / kind).mkdir(parents=True, exist_ok=True)

    corpus_reconstruction().save(root / "reconstruction" / "v2_1.stn")
    corpus_library().save(root / "library" / "v2_0.ins")
    ProjectContainer.save(corpus_project(embedded_reconstruction()), root / "project" / "v1_0.stp")

    for kind, name in (("reconstruction", "v2_1.stn"), ("library", "v2_0.ins"), ("project", "v1_0.stp")):
        path = root / kind / name
        print(f"wrote {path} ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
