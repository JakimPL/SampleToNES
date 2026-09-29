from pathlib import Path
from typing import Final, Optional, Tuple

import numpy as np

from sampletones_core.audio import load_audio, mix_scale, read_stems, scale_stems, write_wave
from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import PulseInstruction
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.reconstruction.recordings import load_recordings
from sampletones_core.reconstructions.reconstruction.stems.channel_assignment import ChannelAssignment
from sampletones_core.reconstructions.reconstruction.stems.data import StemsData
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings

SAMPLES: Final[int] = 64
LEVELS: Final[Tuple[float, ...]] = (0.6, 0.2)
MEASURED_SCALE: Final[float] = 0.4


def _document(paths: Tuple[Path, ...], scale: Optional[float]) -> Reconstruction:
    """A document over one recording per path, each holding one frame of the first pulse."""
    channels = [ChannelName.PULSE1]
    stem_ids = list(range(len(paths)))
    return Reconstruction.create(
        instructions={ChannelName.PULSE1: [PulseInstruction(on=True, pitch=60, volume=8, duty_cycle=0)] * len(paths)},
        config=Config(),
        coefficient=1.0,
        audio_filepath=paths,
        stems_data=StemsData(
            config=StemsConfig(
                entries=[StemEntry(id=stem_id, settings=StemSettings.covering(channels)) for stem_id in stem_ids],
                hierarchy=StemsHierarchy(levels=[stem_ids]),
            ),
            assignments=[ChannelAssignment(channel_name=ChannelName.PULSE1, stem_ids=stem_ids)],
            scale=scale,
        ),
    )


def _written(directory: Path, levels: Tuple[float, ...]) -> Tuple[Path, ...]:
    sample_rate = Config().library.sample_rate
    paths = []
    for index, level in enumerate(levels):
        path = directory / f"stem_{index}.wav"
        write_wave(path, sample_rate, np.full(SAMPLES, level, dtype=np.float32))
        paths.append(path)

    return tuple(paths)


class TestLoadingADocumentsRecordings:
    """A document reads its recordings at the level its conversion read them at."""

    def test_the_recordings_load_at_the_recorded_scale(self, tmp_path: Path) -> None:
        paths = _written(tmp_path, LEVELS)
        general = Config().general

        read = read_stems(paths, target_sample_rate=Config().library.sample_rate)
        assert mix_scale(read, normalize=general.normalize) != MEASURED_SCALE

        recordings = load_recordings(_document(paths, MEASURED_SCALE))

        expected = scale_stems(
            read,
            scale=MEASURED_SCALE,
            quantize=general.quantize,
            quantization_levels=general.quantization_levels,
        )
        assert len(recordings) == len(paths)
        for loaded, reference in zip(recordings, expected):
            np.testing.assert_array_equal(loaded, reference)

    def test_an_unmeasured_record_reads_its_recording_at_its_own_peak(self, tmp_path: Path) -> None:
        """A document written before the scale was recorded reads its one recording as it was converted."""
        (path,) = _written(tmp_path, LEVELS[:1])
        config = Config()

        (recording,) = load_recordings(_document((path,), None))

        np.testing.assert_allclose(
            recording,
            load_audio(
                path,
                target_sample_rate=config.library.sample_rate,
                normalize=config.general.normalize,
                quantize=config.general.quantize,
                quantization_levels=config.general.quantization_levels,
            ),
        )

    def test_a_detached_document_loads_no_recording(self, tmp_path: Path) -> None:
        document = _document(_written(tmp_path, LEVELS), MEASURED_SCALE)
        document.detach_source()

        assert load_recordings(document) == ()
