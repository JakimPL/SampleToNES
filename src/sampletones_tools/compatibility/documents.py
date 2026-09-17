from pathlib import Path
from typing import Any, Dict, Final, List, Sequence, Tuple

from sampletones_core.configs import Config
from sampletones_core.constants.algorithm import RESTING_STEM_ID
from sampletones_core.constants.enums import ChannelName, SpectrumMethod
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
from sampletones_core.project.patterns.pattern import Pattern
from sampletones_core.project.patterns.row import Row
from sampletones_core.project.project import Project
from sampletones_core.project.settings import ProjectSettings
from sampletones_core.project.voices.note_off import NoteOff
from sampletones_core.project.voices.note_on import NoteOn
from sampletones_core.project.voices.sample import Sample
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.reconstruction.stems.channel_assignment import ChannelAssignment
from sampletones_core.reconstructions.reconstruction.stems.data import StemsData
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings

SINGLE_STEM_ID: Final[int] = 0
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
EMBEDDED_CHANNEL: Final[ChannelName] = ChannelName.PULSE2


def corpus_instructions() -> Dict[ChannelName, List[InstructionUnion]]:
    """Three frames on every channel: one sounding, one silent, one sounding.

    The silent frame is what holds a record to naming rest and silence over the same frames, and
    every channel carries one so each instruction class is stored at least once.
    """
    return {
        ChannelName.PULSE1: [
            PulseInstruction(on=True, pitch=45, volume=11, duty_cycle=2),
            PulseInstruction(on=False, pitch=45, volume=0, duty_cycle=0),
            PulseInstruction(on=True, pitch=48, volume=7, duty_cycle=1, detune=2),
        ],
        ChannelName.PULSE2: [
            PulseInstruction(on=True, pitch=52, volume=9, duty_cycle=0),
            PulseInstruction(on=False, pitch=52, volume=0, duty_cycle=0),
            PulseInstruction(on=True, pitch=52, volume=9, duty_cycle=3),
        ],
        ChannelName.TRIANGLE: [
            TriangleInstruction(on=True, pitch=33),
            TriangleInstruction(on=False, pitch=33),
            TriangleInstruction(on=True, pitch=35, coarse_detune=1),
        ],
        ChannelName.NOISE: [
            NoiseInstruction(on=True, period=5, volume=6, short=False),
            NoiseInstruction(on=False, period=5, volume=0, short=False),
            NoiseInstruction(on=True, period=9, volume=12, short=True),
        ],
    }


def stems_record(instructions: Dict[ChannelName, List[InstructionUnion]]) -> StemsData:
    """The single-entry record a classic conversion writes, one owner per frame.

    A frame that sounds answers to the recording; a silent frame answers to rest, which is the
    rule a reconstruction holds its record to.
    """
    channels = list(instructions)
    assignments = [
        ChannelAssignment(
            channel_name=channel_name,
            stem_ids=[SINGLE_STEM_ID if instruction.on else RESTING_STEM_ID for instruction in stream],
        )
        for channel_name, stream in instructions.items()
    ]
    return StemsData.single_entry(StemSettings.covering(channels), assignments)


def corpus_reconstruction(instructions: Dict[ChannelName, List[InstructionUnion]]) -> Reconstruction:
    """A reconstruction naming every channel, its source recording, and one owner per frame."""
    return Reconstruction.create(
        instructions=instructions,
        config=Config(),
        coefficient=COEFFICIENT,
        audio_filepath=(SOURCE_PATH,),
        stems_data=stems_record(instructions),
    )


def embedded_reconstruction() -> Reconstruction:
    """The reconstruction a project carries, sounding one channel while the rest stand by.

    A project detaches a recording from its origin before storing it, so this one names no file,
    which is the shape a stored project holds and the one an upgrade leaves alone.
    """
    instructions: Dict[ChannelName, List[InstructionUnion]] = {
        EMBEDDED_CHANNEL: [
            PulseInstruction(on=True, pitch=40, volume=15, duty_cycle=1),
            PulseInstruction(on=False, pitch=40, volume=0, duty_cycle=0),
        ]
    }
    return Reconstruction.create(
        instructions=instructions,
        config=Config(),
        coefficient=COEFFICIENT,
        audio_filepath=(),
        stems_data=stems_record(instructions),
    )


def library_config() -> Config:
    """The configuration the archived library is analyzed under.

    The spectrum is measured by windowed transform at a gamma above zero, which is where the step
    carrying a library forward has work to do, and the sample rate stands as low as a measured
    sample allows, which is what keeps the archived file small.
    """
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
    generator = PulseGenerator(config, ChannelName.PULSE1)
    fragments: Dict[InstructionUnion, InstructionLibraryFragment[Any]] = {
        instruction: InstructionLibraryFragment.create(generator, instruction, extractor)
        for instruction in library_tones()
    }
    return InstructionLibraryData.create(config, fragments)


def corpus_project(reconstruction: Reconstruction) -> Project:
    """A project arranging one reconstruction under two voices.

    Two voices sharing one reconstruction is what holds a stored project to keeping a single copy
    of it, and the rows name a voice, let it go, and stand empty, so every note column a row can
    hold is stored.
    """
    project = Project.create(
        title=PROJECT_TITLE,
        author=PROJECT_AUTHOR,
        comment=PROJECT_COMMENT,
        rows_per_pattern=ROWS_PER_PATTERN,
        settings=ProjectSettings(tempo=PROJECT_TEMPO),
    )
    first = Sample(name=FIRST_SAMPLE_NAME, reconstruction=reconstruction)
    second = Sample(name=SECOND_SAMPLE_NAME, reconstruction=reconstruction)
    project.voices.append(first)
    project.voices.append(second)
    project.song.channels[EMBEDDED_CHANNEL].patterns[0] = Pattern(
        name=PATTERN_NAME,
        rows=_rows(first.id, second.id),
    )
    return project


def _rows(first_voice_id: str, second_voice_id: str) -> List[Row]:
    """The lines one pattern holds: a note, a second note carrying its columns, a note-off, a blank."""
    return [
        Row(command=NoteOn(voice_id=first_voice_id)),
        Row(command=NoteOn(voice_id=second_voice_id), transpose=ROW_TRANSPOSE, volume=ROW_VOLUME),
        Row(command=NoteOff()),
        Row(),
    ]


def corpus_channels() -> Sequence[ChannelName]:
    """The channels the archived reconstruction plays, which is every one of them."""
    return tuple(corpus_instructions())
