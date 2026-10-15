from typing import Final, List, Tuple

import numpy as np
import pytest

from sampletones_application.logic.shared.live import LiveSound, SoundingNote
from sampletones_application.logic.shared.synthesis import ChannelBank, EngineRates, synthesize_tick
from sampletones_core.audio import clip_audio_inplace, silence
from sampletones_core.configs import Config
from tests.suite.live import held_instrument, instrument_sound, sample_sound, short_sample

STRUCK_PITCH: Final[int] = 67
SAMPLE_FRAMES: Final[int] = 4
TICKS: Final[int] = 12
BLOCK_LENGTHS: Final[Tuple[int, ...]] = (100, 1000, 333, 2048, 7)
LONG_BLOCK: Final[int] = 8192
MID_TICK: Final[int] = 500
EVEN_RATE: Final[int] = 44100
UNEVEN_RATE: Final[int] = 32000


@pytest.fixture
def config() -> Config:
    return Config()


@pytest.fixture
def held(config: Config) -> LiveSound:
    return instrument_sound(held_instrument(), note=STRUCK_PITCH, config=config)


def _bank(config: Config, output_rate: int) -> ChannelBank:
    return ChannelBank(config, EngineRates.from_config(config, output_rate))


def _ticked(sound: LiveSound, bank: ChannelBank, ticks: int) -> np.ndarray:
    """What ``sound`` sounds for ``ticks`` ticks synthesized one by one on ``bank``, as a row's ticks are."""
    note = sound.note()
    audio: List[np.ndarray] = []
    for tick in range(ticks):
        frame_length = bank.clock.frame_length(tick)
        block = silence(frame_length)
        for channel_name, instruction in note.tick().items():
            block += synthesize_tick(bank.generator(channel_name), instruction, frame_length)

        audio.append(clip_audio_inplace(block))

    return np.concatenate(audio)


def _filled(note: SoundingNote, lengths: Tuple[int, ...]) -> np.ndarray:
    blocks: List[np.ndarray] = []
    for length in lengths:
        block = silence(length)
        frames = note.fill(block)
        blocks.append(block[:frames])

    return np.concatenate(blocks)


class TestBlocksOfAnyLength:
    """A note handed out in blocks of any length sounds the ticks a row's walk synthesizes one by one."""

    @pytest.mark.parametrize("output_rate", [EVEN_RATE, UNEVEN_RATE], ids=["whole-ticks", "uneven-ticks"])
    def test_blocks_carry_the_ticks_whole(self, held: LiveSound, config: Config, output_rate: int) -> None:
        ticked = _ticked(held, _bank(config, output_rate), TICKS)
        lengths = BLOCK_LENGTHS + (len(ticked) - sum(BLOCK_LENGTHS),)

        filled = _filled(SoundingNote(held.note(), _bank(config, output_rate)), lengths)

        assert np.any(ticked)
        np.testing.assert_array_equal(filled, ticked)


class TestAStrikeStartsFromRest:
    """A strike starts the generators it sounds on from rest, as a row starting a note does."""

    def test_a_second_strike_on_one_bank_sounds_as_the_first(self, held: LiveSound, config: Config) -> None:
        bank = _bank(config, EVEN_RATE)
        first = SoundingNote(held.note(), bank)
        opening = _filled(first, BLOCK_LENGTHS)

        again = _filled(SoundingNote(held.note(), bank), BLOCK_LENGTHS)

        np.testing.assert_array_equal(again, opening)

    def test_a_generator_left_running_sounds_otherwise(self, held: LiveSound, config: Config) -> None:
        bank = _bank(config, EVEN_RATE)
        opening = _filled(SoundingNote(held.note(), bank), BLOCK_LENGTHS)

        carried_on = _ticked(held, bank, TICKS)[: len(opening)]

        assert not np.array_equal(carried_on, opening)


class TestWhereANoteEnds:
    """A recording ends with its last tick, a held instrument sounds on, and a release ends a note at once."""

    def test_a_recording_ends_with_its_last_tick(self, config: Config) -> None:
        sound = sample_sound(short_sample(SAMPLE_FRAMES), step=0, config=config)
        bank = _bank(config, EVEN_RATE)
        note = SoundingNote(sound.note(), bank)
        block = silence(LONG_BLOCK)

        frames = note.fill(block)

        assert frames == sum(bank.clock.frame_length(tick) for tick in range(SAMPLE_FRAMES))
        assert np.any(block[:frames])
        assert note.finished
        assert note.fill(silence(LONG_BLOCK)) == 0

    def test_a_held_instrument_fills_every_block(self, held: LiveSound, config: Config) -> None:
        note = SoundingNote(held.note(), _bank(config, EVEN_RATE))

        assert note.fill(silence(LONG_BLOCK)) == LONG_BLOCK
        assert note.fill(silence(LONG_BLOCK)) == LONG_BLOCK
        assert not note.finished

    def test_a_release_ends_the_note_mid_tick(self, held: LiveSound, config: Config) -> None:
        note = SoundingNote(held.note(), _bank(config, EVEN_RATE))
        note.fill(silence(MID_TICK))

        note.release()

        assert note.finished
        assert note.fill(silence(LONG_BLOCK)) == 0

    def test_a_note_held_on_fills_past_the_tick(self, held: LiveSound, config: Config) -> None:
        note = SoundingNote(held.note(), _bank(config, EVEN_RATE))
        note.fill(silence(MID_TICK))
        block = silence(LONG_BLOCK)

        assert note.fill(block) == LONG_BLOCK
        assert np.any(block)
