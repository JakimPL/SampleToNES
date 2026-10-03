from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Final, List, Tuple

from sampletones_core.compatibility.kind import ObjectKind
from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import InstructionUnion, NoiseInstruction, PulseInstruction, TriangleInstruction
from sampletones_core.reconstructions import Reconstruction
from tests.suite.compatibility import ARCHIVED_VERSIONS, archived
from tests.suite.screens.seeds.constants import TURNING_LEVELS
from tests.suite.stems import recorded_from, single_entry_stems_data

LINE_START_PITCH: Final[int] = 60
LINE_STEP_FRAMES: Final[int] = 15
LINE_SPAN: Final[int] = 12
LINE_VOLUME: Final[int] = 12
LINE_DUTY_CYCLE: Final[int] = 2
BASS_PITCH: Final[int] = 45
BEAT_FRAMES: Final[int] = 15
BEAT_LENGTH: Final[int] = 3
BEAT_PERIOD: Final[int] = 4
BEAT_VOLUME: Final[int] = 10
TURNING_PULSE_PITCH: Final[int] = 40
TURNING_PULSE_SPAN: Final[int] = 24
TURNING_SECOND_PITCH: Final[int] = 30
TURNING_SECOND_SPAN: Final[int] = 31
TURNING_TRIANGLE_PITCH: Final[int] = 30
TURNING_TRIANGLE_SPAN: Final[int] = 29
TURNING_PERIODS: Final[int] = 16
TURNING_DUTY_CYCLES: Final[int] = 4
TURNING_SECOND_LEVEL_STEP: Final[int] = 7
TURNING_NOISE_LEVEL_STEP: Final[int] = 5
TURNING_SECOND_DUTY_TICKS: Final[int] = 3


@dataclass(frozen=True)
class StoredReconstruction:
    """The reconstruction the last release wrote, laid at ``destination`` the way this build writes it.

    It names the recording :func:`stored_recording` lays in the home, so it opens with its source.
    """

    destination: Path

    def write(self) -> None:
        """Saves the reconstruction to the destination."""
        self.destination.parent.mkdir(parents=True, exist_ok=True)
        _stored_reconstruction().save(self.destination)


@dataclass(frozen=True)
class PlayableReconstruction:
    """A reconstruction sounding a rising line on Pulse 1, a bass on the triangle and a beat on the noise.

    Each recording of ``recordings`` plays the ``frames`` frames once, in turn, so the document
    lasts as long as the recordings laid at those paths, one :class:`Recording` of ``frames`` frames
    each, and opens with its sources.
    """

    destination: Path
    recordings: Tuple[Path, ...]
    frames: int

    def write(self) -> None:
        """Saves the reconstruction to the destination, naming each recording as a source."""
        instructions = _playable_instructions(self.frames)
        reconstruction = Reconstruction.create(
            instructions=instructions,
            config=Config(),
            coefficient=1.0,
            audio_filepath=self.recordings[:1],
            stems_data=single_entry_stems_data(list(instructions), instructions),
        )
        if len(self.recordings) > 1:
            reconstruction = recorded_from(reconstruction, self.recordings)

        self.destination.parent.mkdir(parents=True, exist_ok=True)
        reconstruction.save(self.destination)


def _playable_instructions(frames: int) -> Dict[ChannelName, List[InstructionUnion]]:
    """The instructions of ``frames`` frames: a rising line, a bass and a beat on three channels."""
    line: List[InstructionUnion] = [
        PulseInstruction(
            on=True,
            pitch=LINE_START_PITCH + (frame // LINE_STEP_FRAMES) % LINE_SPAN,
            volume=LINE_VOLUME,
            duty_cycle=LINE_DUTY_CYCLE,
        )
        for frame in range(frames)
    ]
    bass: List[InstructionUnion] = [TriangleInstruction(on=True, pitch=BASS_PITCH) for _ in range(frames)]
    beat: List[InstructionUnion] = [
        NoiseInstruction(
            on=frame % BEAT_FRAMES < BEAT_LENGTH,
            period=BEAT_PERIOD,
            volume=BEAT_VOLUME if frame % BEAT_FRAMES < BEAT_LENGTH else 0,
            short=False,
        )
        for frame in range(frames)
    ]
    return {ChannelName.PULSE1: line, ChannelName.TRIANGLE: bass, ChannelName.NOISE: beat}


def _turning_instructions(ticks: int) -> Dict[ChannelName, List[InstructionUnion]]:
    """Every channel sounding a new pitch, level or period at each of ``ticks`` ticks."""
    return {
        ChannelName.PULSE1: [
            PulseInstruction(
                on=True,
                pitch=TURNING_PULSE_PITCH + tick % TURNING_PULSE_SPAN,
                volume=1 + tick % TURNING_LEVELS,
                duty_cycle=tick % TURNING_DUTY_CYCLES,
            )
            for tick in range(ticks)
        ],
        ChannelName.PULSE2: [
            PulseInstruction(
                on=True,
                pitch=TURNING_SECOND_PITCH + tick % TURNING_SECOND_SPAN,
                volume=1 + (tick * TURNING_SECOND_LEVEL_STEP) % TURNING_LEVELS,
                duty_cycle=(tick // TURNING_SECOND_DUTY_TICKS) % TURNING_DUTY_CYCLES,
            )
            for tick in range(ticks)
        ],
        ChannelName.TRIANGLE: [
            TriangleInstruction(on=True, pitch=TURNING_TRIANGLE_PITCH + tick % TURNING_TRIANGLE_SPAN)
            for tick in range(ticks)
        ],
        ChannelName.NOISE: [
            NoiseInstruction(
                on=True,
                period=tick % TURNING_PERIODS,
                volume=1 + (tick * TURNING_NOISE_LEVEL_STEP) % TURNING_LEVELS,
                short=bool(tick % 2),
            )
            for tick in range(ticks)
        ],
    }


def _detached_reconstruction(
    instructions: Dict[ChannelName, List[InstructionUnion]],
    config: Config,
) -> Reconstruction:
    """A reconstruction of ``instructions`` naming no recording, the way a project stores a sample."""
    return Reconstruction.create(
        instructions=instructions,
        config=config,
        coefficient=1.0,
        audio_filepath=(),
        stems_data=single_entry_stems_data(list(instructions), instructions),
    )


def _stored_reconstruction() -> Reconstruction:
    """The reconstruction the compatibility corpus keeps for the release that wrote it."""
    return Reconstruction.load(archived(ObjectKind.RECONSTRUCTION, ARCHIVED_VERSIONS[ObjectKind.RECONSTRUCTION]))
