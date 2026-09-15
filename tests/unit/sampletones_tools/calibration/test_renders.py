from pathlib import Path
from typing import Dict, Final, List

import numpy as np

from sampletones_core.audio.io import read_wave
from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import InstructionUnion, NoiseInstruction, PulseInstruction
from sampletones_shared.paths.extensions import EXT_FILE_JSON, EXT_FILE_WAVE
from sampletones_shared.utils.system.paths import get_filename
from sampletones_tools.calibration.layout import RENDERS_DIRECTORY
from sampletones_tools.calibration.renders import RenderRecord, sounding_timelines, write_render

SAMPLE_RATE: Final[int] = 22050
FREQUENCY: Final[float] = 220.0


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
        rendered, sample_rate = read_wave(directory / get_filename(record.item, EXT_FILE_WAVE))
        assert sample_rate == SAMPLE_RATE
        assert np.allclose(rendered, audio, atol=1e-6)
