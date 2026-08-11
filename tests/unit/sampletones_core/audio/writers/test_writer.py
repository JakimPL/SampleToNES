from pathlib import Path
from typing import Dict, Final, Tuple

import numpy as np
import pytest
import soundfile

from sampletones_core.audio.writers import (
    AUDIO_DEPTHS,
    MP3_SAMPLE_RATES,
    AudioDepth,
    AudioFormat,
    AudioOutputSpec,
    Mp3OutputSpec,
    WaveOutputSpec,
    available_audio_formats,
    available_depths,
    open_audio_writer,
)
from sampletones_shared.exceptions import AudioWriteError
from tests.suite.base import BaseTestSuite

SAMPLE_RATE: Final[int] = 44100
SECONDS: Final[float] = 1.0
CHUNK: Final[int] = 367
TONE_FREQUENCY: Final[float] = 440.0
DEPTH_TOLERANCES: Final[Dict[AudioDepth, float]] = {
    AudioDepth.PCM_U8: 1.0 / 128,
    AudioDepth.PCM_16: 1.0 / 32768,
    AudioDepth.PCM_24: 1.0 / 8388608,
    AudioDepth.PCM_32: 1.0 / 8388608,
    AudioDepth.FLOAT_32: 1e-6,
}


def _tone(sample_rate: int, seconds: float = SECONDS) -> np.ndarray:
    samples = int(sample_rate * seconds)
    return (0.5 * np.sin(2 * np.pi * TONE_FREQUENCY * np.arange(samples) / sample_rate)).astype(np.float32)


def _chunks(audio: np.ndarray, size: int = CHUNK) -> Tuple[np.ndarray, ...]:
    return tuple(audio[offset : offset + size] for offset in range(0, len(audio), size))


def _write(path: Path, spec: AudioOutputSpec, audio: np.ndarray) -> None:
    with open_audio_writer(path, spec) as writer:
        for chunk in _chunks(audio):
            writer.write(chunk)


class TestTheEncoderIsProbed(BaseTestSuite):
    """What the registry declares is offered only where the installed encoder also writes it."""

    def test_wave_is_always_available(self) -> None:
        assert AudioFormat.WAVE in available_audio_formats()

    def test_the_offered_depths_are_the_declared_ones_the_encoder_writes(self) -> None:
        assert set(available_depths(AudioFormat.WAVE)) <= set(AUDIO_DEPTHS)

    def test_a_format_that_sets_its_own_depth_offers_none(self) -> None:
        assert available_depths(AudioFormat.MP3) == ()


class TestWaveRoundTrip(BaseTestSuite):
    """Audio written a chunk at a time reads back whole, at the depth it was asked for."""

    @pytest.mark.parametrize("depth", AUDIO_DEPTHS)
    def test_a_render_reads_back_at_its_depth(self, tmp_path: Path, depth: AudioDepth) -> None:
        audio = _tone(SAMPLE_RATE)
        path = tmp_path / f"render{WaveOutputSpec(sample_rate=SAMPLE_RATE).extension}"

        _write(path, WaveOutputSpec(sample_rate=SAMPLE_RATE, depth=depth), audio)
        restored, sample_rate = soundfile.read(path, dtype="float32")

        assert sample_rate == SAMPLE_RATE
        assert len(restored) == len(audio)
        assert float(np.abs(restored - audio).max()) <= DEPTH_TOLERANCES[depth]

    @pytest.mark.parametrize("sample_rate", (8000, 22050, 48000, 96000, 192000))
    def test_every_offered_rate_is_written(self, tmp_path: Path, sample_rate: int) -> None:
        audio = _tone(sample_rate, seconds=0.1)
        path = tmp_path / "render.wav"

        _write(path, WaveOutputSpec(sample_rate=sample_rate), audio)
        info = soundfile.info(path)

        assert info.samplerate == sample_rate
        assert info.frames == len(audio)

    def test_chunks_of_differing_lengths_are_written_whole(self, tmp_path: Path) -> None:
        """A row varies in length where the tick clock spreads a fraction, so chunks do too."""
        path = tmp_path / "render.wav"
        lengths = (367, 368, 367, 1, 4096, 12)
        audio = _tone(SAMPLE_RATE)

        offset = 0
        with open_audio_writer(path, WaveOutputSpec(sample_rate=SAMPLE_RATE)) as writer:
            for length in lengths:
                writer.write(audio[offset : offset + length])
                offset += length

        assert soundfile.info(path).frames == sum(lengths)

    def test_a_finished_file_stands_on_its_own(self, tmp_path: Path) -> None:
        path = tmp_path / "render.wav"

        _write(path, WaveOutputSpec(sample_rate=SAMPLE_RATE), _tone(SAMPLE_RATE))

        assert path.exists()
        assert path.stat().st_size > 0


class TestMp3RoundTrip(BaseTestSuite):
    @pytest.mark.parametrize("sample_rate", MP3_SAMPLE_RATES)
    def test_a_render_reads_back_at_its_rate(self, tmp_path: Path, sample_rate: int) -> None:
        audio = _tone(sample_rate)
        path = tmp_path / "render.mp3"

        _write(path, Mp3OutputSpec.at(sample_rate), audio)
        info = soundfile.info(path)

        assert info.samplerate == sample_rate
        assert info.frames == len(audio)

    @pytest.mark.parametrize("bitrate", (320, 192, 128, 64))
    def test_the_encoded_rate_follows_the_chosen_bitrate(self, tmp_path: Path, bitrate: int) -> None:
        """The ladder is what makes a bitrate choice mean something, so it is measured."""
        seconds = 8.0
        audio = _tone(SAMPLE_RATE, seconds=seconds)
        path = tmp_path / "render.mp3"

        _write(path, Mp3OutputSpec(sample_rate=SAMPLE_RATE, bitrate=bitrate), audio)
        measured = path.stat().st_size * 8 / seconds / 1000

        assert abs(measured - bitrate) < 0.05 * bitrate

    def test_a_higher_bitrate_makes_a_larger_file(self, tmp_path: Path) -> None:
        audio = _tone(SAMPLE_RATE, seconds=4.0)
        sizes = []
        for bitrate in (64, 128, 320):
            path = tmp_path / f"render_{bitrate}.mp3"
            _write(path, Mp3OutputSpec(sample_rate=SAMPLE_RATE, bitrate=bitrate), audio)
            sizes.append(path.stat().st_size)

        assert sizes == sorted(sizes)


class TestTheWriterOwnsItsFile(BaseTestSuite):
    def test_writing_outside_the_block_is_refused(self, tmp_path: Path) -> None:
        writer = open_audio_writer(tmp_path / "render.wav", WaveOutputSpec(sample_rate=SAMPLE_RATE))

        with pytest.raises(AudioWriteError, match="write within the writer's context"):
            writer.write(_tone(SAMPLE_RATE, seconds=0.01))

    def test_writing_after_the_block_is_refused(self, tmp_path: Path) -> None:
        path = tmp_path / "render.wav"
        with open_audio_writer(path, WaveOutputSpec(sample_rate=SAMPLE_RATE)) as writer:
            writer.write(_tone(SAMPLE_RATE, seconds=0.01))

        with pytest.raises(AudioWriteError, match="write within the writer's context"):
            writer.write(_tone(SAMPLE_RATE, seconds=0.01))

    def test_a_render_interrupted_partway_leaves_a_readable_file(self, tmp_path: Path) -> None:
        """A cancel leaves the file finalized, so the caller decides whether to keep it."""
        path = tmp_path / "render.wav"
        audio = _tone(SAMPLE_RATE)
        written = 0

        with open_audio_writer(path, WaveOutputSpec(sample_rate=SAMPLE_RATE)) as writer:
            for chunk in _chunks(audio)[:10]:
                writer.write(chunk)
                written += len(chunk)

        assert soundfile.info(path).frames == written
