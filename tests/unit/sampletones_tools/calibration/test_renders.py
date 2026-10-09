from pathlib import Path
from typing import Dict, Final, List

import numpy as np

from sampletones_core.audio.io import read_wave
from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import InstructionUnion, NoiseInstruction, PulseInstruction
from sampletones_shared.paths.extensions import EXT_FILE_FLAC, EXT_FILE_JSON
from sampletones_shared.utils.system.paths import get_filename
from sampletones_tools.calibration.layout import RENDERS_DIRECTORY, combination_name
from sampletones_tools.calibration.renders import (
    RenderRecord,
    channel_subsets,
    item_directory,
    sounding_timelines,
    write_channel_renders,
    write_render,
)

SAMPLE_RATE: Final[int] = 22050
FREQUENCY: Final[float] = 220.0
VARIANT: Final[str] = "fft-pe1"
ITEM: Final[str] = "tone-a"
QUANTIZATION_TOLERANCE: Final[float] = 1.0 / 2**15


class TestSoundingTimelines:
    def test_every_channel_marks_the_frames_it_sounds(self) -> None:
        sounding = PulseInstruction(on=True, pitch=60, volume=8, duty_cycle=1)
        resting = PulseInstruction.null_instruction()
        instructions: Dict[ChannelName, List[InstructionUnion]] = {
            ChannelName.PULSE1: [sounding, resting, sounding],
            ChannelName.NOISE: [NoiseInstruction.null_instruction()] * 3,
        }

        assert sounding_timelines(instructions) == {"pulse1": "101", "noise": "000"}


class TestWriteRender:
    def test_a_render_lands_beside_the_record_that_reads_back_unchanged(self, tmp_path: Path) -> None:
        record = RenderRecord(
            variant="fft-pe1",
            item="tone-a",
            position=0,
            category="tone",
            timelines={"pulse1": "0110", "triangle": "1111"},
            judgments={"referee": {"score": 1.25, "missing": 0.5}},
            silence={"referee": 50.0},
        )
        audio = 0.5 * np.sin(2.0 * np.pi * FREQUENCY * np.arange(SAMPLE_RATE // 4) / SAMPLE_RATE)

        write_render(tmp_path, record, audio, SAMPLE_RATE)

        directory = tmp_path / RENDERS_DIRECTORY / record.variant
        written = directory / get_filename(record.item, EXT_FILE_JSON)
        assert RenderRecord.model_validate_json(written.read_text(encoding="utf-8")) == record
        rendered, sample_rate = read_wave(directory / get_filename(record.item, EXT_FILE_FLAC))
        assert sample_rate == SAMPLE_RATE
        assert np.allclose(rendered, audio, atol=QUANTIZATION_TOLERANCE)


class TestChannelSubsets:
    def test_one_channel_leaves_nothing_to_switch(self) -> None:
        assert channel_subsets([ChannelName.NOISE]) == []

    def test_every_part_short_of_the_whole_is_offered(self) -> None:
        channels = [ChannelName.PULSE1, ChannelName.TRIANGLE, ChannelName.NOISE]

        subsets = channel_subsets(channels)

        assert len(subsets) == 2 ** len(channels) - 2
        assert tuple(channels) not in subsets
        assert (ChannelName.PULSE1,) in subsets


class TestWriteChannelRenders:
    def test_the_parts_add_up_to_the_whole_render(self, tmp_path: Path) -> None:
        approximations = _approximations()

        write_channel_renders(tmp_path, VARIANT, ITEM, approximations, SAMPLE_RATE)

        directory = item_directory(tmp_path, VARIANT, ITEM)
        parts = [
            read_wave(directory / get_filename(combination_name([channel]), EXT_FILE_FLAC))[0]
            for channel in approximations
        ]
        tolerance = len(parts) * QUANTIZATION_TOLERANCE
        assert np.allclose(sum(parts), sum(approximations.values()), atol=tolerance)

    def test_a_part_stands_beside_the_whole_it_is_cut_from(self, tmp_path: Path) -> None:
        approximations = _approximations()

        written = write_channel_renders(tmp_path, VARIANT, ITEM, approximations, SAMPLE_RATE)

        directory = item_directory(tmp_path, VARIANT, ITEM)
        assert len(written) == 2 ** len(approximations) - 2
        for subset in written:
            assert (directory / get_filename(combination_name(subset), EXT_FILE_FLAC)).is_file()

    def test_a_render_of_one_channel_writes_no_part(self, tmp_path: Path) -> None:
        written = write_channel_renders(
            tmp_path,
            VARIANT,
            ITEM,
            {ChannelName.NOISE: _tone(FREQUENCY)},
            SAMPLE_RATE,
        )

        assert written == []
        assert not item_directory(tmp_path, VARIANT, ITEM).exists()


def _tone(frequency: float) -> np.ndarray:
    steps = np.arange(SAMPLE_RATE // 4)
    return (0.25 * np.sin(2.0 * np.pi * frequency * steps / SAMPLE_RATE)).astype(np.float32)


def _approximations() -> Dict[ChannelName, np.ndarray]:
    return {
        ChannelName.PULSE1: _tone(FREQUENCY),
        ChannelName.TRIANGLE: _tone(2.0 * FREQUENCY),
        ChannelName.NOISE: _tone(3.0 * FREQUENCY),
    }
