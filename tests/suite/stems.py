from pathlib import Path
from typing import Dict, Final, List, Mapping, Sequence, Tuple

import numpy as np
import pytest

from sampletones_core.audio import write_wave
from sampletones_core.configs import Config
from sampletones_core.constants.algorithm import RESTING_STEM_ID
from sampletones_core.constants.enums import ChannelName, HierarchyMode, bending_channels
from sampletones_core.exporters import CHANNEL_TO_EXPORTER_MAP, Features
from sampletones_core.instructions import InstructionUnion, PulseInstruction
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.reconstruction.instructions import InstructionsItem
from sampletones_core.reconstructions.reconstruction.stems.channel_assignment import ChannelAssignment
from sampletones_core.reconstructions.reconstruction.stems.data import StemsData
from sampletones_core.reconstructions.reconstruction.stems.selection import StemSelection
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from sampletones_shared.types.path import Pathlike

SINGLE_STEM_ID: Final[int] = 0
STEM_A_ID: Final[int] = 0
STEM_B_ID: Final[int] = 1
STEM_C_ID: Final[int] = 2
THREE_STEM_CHANNELS: Final[List[ChannelName]] = [
    ChannelName.PULSE1,
    ChannelName.PULSE2,
    ChannelName.TRIANGLE,
    ChannelName.NOISE,
]
THREE_STEM_ENTRY_CHANNELS: Final[Dict[int, List[ChannelName]]] = {
    STEM_A_ID: [ChannelName.PULSE1, ChannelName.TRIANGLE, ChannelName.NOISE],
    STEM_B_ID: [ChannelName.PULSE2, ChannelName.TRIANGLE],
    STEM_C_ID: [ChannelName.PULSE1, ChannelName.NOISE],
}
STEM_RECORDING_DURATION_SECONDS: Final[float] = 0.5
RECORDED_SCALE: Final[float] = 1.0
RECORDING_SEED: Final[int] = 93
SHARED_CHANNEL: Final[ChannelName] = ChannelName.PULSE1
SOLE_CHANNEL: Final[ChannelName] = ChannelName.PULSE2
SHARED_OWNERS: Final[Tuple[int, ...]] = (STEM_A_ID, STEM_B_ID)
TAKING_TURNS_PITCH: Final[int] = 60
TAKING_TURNS_VOLUME: Final[int] = 8
TAKING_TURNS_DUTY_CYCLE: Final[int] = 0


def single_entry_stems_data(
    channels: List[ChannelName],
    instructions: Mapping[ChannelName, Sequence[InstructionUnion]],
) -> StemsData:
    """The single-entry record for ``channels``, stem 0 owning each frame that sounds and bending them.

    Rest and silence name the same frames, so a silent frame takes the resting stem id, which is
    the shape a conversion records.
    """
    assignments = [
        ChannelAssignment(
            channel_name=channel_name,
            stem_ids=[SINGLE_STEM_ID if instruction.on else RESTING_STEM_ID for instruction in stream],
        )
        for channel_name, stream in instructions.items()
        if stream
    ]
    return StemsData.single_entry(StemSettings.covering(channels), assignments, RECORDED_SCALE)


def three_stem_config() -> StemsConfig:
    """Builds the three-stem setup the stems tests share.

    Stems a (pulse 1, triangle, noise) and b (pulse 2, triangle) pick on the first
    hierarchy level, stem c (pulse 1, noise) on the second, each sounding one channel at a time.
    """
    return StemsConfig(
        entries=[
            StemEntry(
                id=stem_id,
                settings=StemSettings(channels=channels, bends=bending_channels(channels), channel_cap=1),
            )
            for stem_id, channels in THREE_STEM_ENTRY_CHANNELS.items()
        ],
        hierarchy=StemsHierarchy(
            levels=[[STEM_A_ID, STEM_B_ID], [STEM_C_ID]],
            mode=HierarchyMode.STRICT,
        ),
    )


def three_stem_reconstruction_config() -> Config:
    """Builds a reconstruction config for the three-stem example."""
    return Config()


def write_three_stem_recordings(
    config: Config,
    tmp_dir: Pathlike,
) -> Tuple[Path, Path, Path]:
    """Writes three distinct stem recordings a, b, c and returns their paths in order."""
    sample_rate = config.library.sample_rate
    count = int(sample_rate * STEM_RECORDING_DURATION_SECONDS)
    time = np.arange(count) / sample_rate
    recordings = {
        "a": 0.5 * np.sin(2 * np.pi * 440.0 * time),
        "b": 0.4 * np.sin(2 * np.pi * 220.0 * time),
        "c": np.random.default_rng(RECORDING_SEED).uniform(-0.3, 0.3, count),
    }

    paths: List[Path] = []
    for name, audio in recordings.items():
        path = Path(tmp_dir) / f"stem_{name}.wav"
        write_wave(path, sample_rate, audio)
        paths.append(path)

    return paths[0], paths[1], paths[2]


def everything_heard(reconstruction: Reconstruction) -> StemSelection:
    """The reader listening to every recording on every channel, as a fresh document reads."""
    return StemSelection.everywhere(
        frozenset(reconstruction.stems_data.config.entries_by_id),
        ChannelName.items(),
    )


def regenerated(
    reconstruction: Reconstruction,
    channel_name: ChannelName,
    features: Features,
) -> Reconstruction:
    """The document a regeneration leaves once it rebuilds one channel from ``features``, every recording heard."""
    rebuilt = reconstruction.model_copy(deep=True)
    rebuilt.update_channel_data(
        channel_name,
        list(CHANNEL_TO_EXPORTER_MAP[channel_name].from_features(features)),
        features.initial_pitch,
        features.held_features,
        heard=rebuilt.recorded_stem_ids,
    )
    return rebuilt


def recorded_from(
    reconstruction: Reconstruction,
    paths: Sequence[Path],
) -> Reconstruction:
    """The document as though its recordings had been read from ``paths``, one per entry.

    A test states the files a conversion would have read, and the record takes its sources from
    them; the entries follow, one per path over the channels the document already plays. Every
    recording a document names holds a frame, so each channel plays its stream once per recording,
    and the frames sounding in the n-th play answer to the n-th recording.
    """
    settings = reconstruction.stems_data.config.entries[0].settings
    stem_ids = list(range(len(paths)))
    streams = dict(reconstruction.streams)
    assignments: List[ChannelAssignment] = []
    for channel_name in reconstruction.playing_channels:
        stream = reconstruction.instructions[channel_name]
        streams[channel_name] = InstructionsItem.create(
            channel_name=channel_name,
            instructions=stream * len(paths),
            initial_pitch=reconstruction.initial_pitches[channel_name],
            held_features=reconstruction.held_features[channel_name],
        )
        assignments.append(
            ChannelAssignment(
                channel_name=channel_name,
                stem_ids=[
                    stem_id if instruction.on else RESTING_STEM_ID for stem_id in stem_ids for instruction in stream
                ],
            )
        )

    stems_data = StemsData(
        config=StemsConfig(
            entries=[StemEntry(id=stem_id, settings=settings) for stem_id in stem_ids],
            hierarchy=StemsHierarchy(levels=[stem_ids]),
        ),
        assignments=assignments,
        scale=RECORDED_SCALE,
    ).with_sources(paths)
    return reconstruction.rewritten(streams, stems_data)


def taking_turns_reconstruction(sources: Sequence[Path]) -> Reconstruction:
    """Two recordings taking turns on the shared channel, the second holding the sole channel alone.

    The shared channel plays one frame per recording, the first recording's and then the second's,
    and the sole channel plays one frame of the second recording. Taking the second recording out
    therefore releases a frame on each channel, and leaves the sole channel standing by.

    Args:
        sources: The files the two recordings were read from, the first recording's first.
    """
    instruction = PulseInstruction(
        on=True,
        pitch=TAKING_TURNS_PITCH,
        volume=TAKING_TURNS_VOLUME,
        duty_cycle=TAKING_TURNS_DUTY_CYCLE,
    )
    instructions: Dict[ChannelName, List[InstructionUnion]] = {
        SHARED_CHANNEL: [instruction] * len(SHARED_OWNERS),
        SOLE_CHANNEL: [instruction],
    }
    stems_data = StemsData(
        config=StemsConfig(
            entries=[
                StemEntry(id=STEM_A_ID, settings=StemSettings.covering([SHARED_CHANNEL])),
                StemEntry(id=STEM_B_ID, settings=StemSettings.covering([SHARED_CHANNEL, SOLE_CHANNEL])),
            ],
            hierarchy=StemsHierarchy(levels=[[STEM_A_ID, STEM_B_ID]]),
        ),
        assignments=[
            ChannelAssignment(channel_name=SHARED_CHANNEL, stem_ids=list(SHARED_OWNERS)),
            ChannelAssignment(channel_name=SOLE_CHANNEL, stem_ids=[STEM_B_ID]),
        ],
        scale=RECORDED_SCALE,
    ).with_sources(sources)
    return Reconstruction.create(
        instructions=instructions,
        config=Config(),
        coefficient=1.0,
        audio_filepath=tuple(sources),
        stems_data=stems_data,
    )


@pytest.fixture
def taking_turns(tmp_path: Path) -> Reconstruction:
    """The two-recording document, naming recordings this machine holds nowhere."""
    return taking_turns_reconstruction((tmp_path / "a.wav", tmp_path / "b.wav"))


@pytest.fixture
def taking_turns_file(tmp_path: Path) -> Path:
    """The two-recording document saved to a file beside the recordings it was read from."""
    recordings = tmp_path / "recordings"
    recordings.mkdir()
    first, second, _ = write_three_stem_recordings(three_stem_reconstruction_config(), recordings)
    path = tmp_path / "turns.stn"
    taking_turns_reconstruction((first, second)).save(path)
    return path
