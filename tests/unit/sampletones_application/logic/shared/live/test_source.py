from typing import Final, List

import numpy as np
import pytest

from sampletones_application.logic.shared.live import Keyboard, LiveKey, LiveNoteSource, LiveSound, Strike
from sampletones_core.audio import silence
from sampletones_core.audio.output import Fill
from sampletones_core.configs import Config
from tests.suite.live import held_instrument, instrument_sound, sample_sound, short_sample, strike

OUTPUT_RATE: Final[int] = 44100
BLOCK: Final[int] = 1024
LINGER_SECONDS: Final[float] = 0.1
LINGER_FRAMES: Final[int] = round(LINGER_SECONDS * OUTPUT_RATE)
NO_LINGER: Final[float] = 0.0
LOW: Final[int] = 60
HIGH: Final[int] = 67
SAMPLE_FRAMES: Final[int] = 4
PAL_FREQUENCY: Final[int] = 50
OPENING_BLOCKS: Final[int] = 3
ENOUGH_BLOCKS: Final[int] = 400


def _unexpected(error: Exception) -> None:
    raise AssertionError(f"a live source told a failure between reads: {error}")


def _begun(source: LiveNoteSource) -> LiveNoteSource:
    source.begin(OUTPUT_RATE, _unexpected)
    return source


def _read(source: LiveNoteSource) -> Fill[None]:
    return source.read_into(silence(BLOCK))


def _blocks(source: LiveNoteSource, count: int) -> List[np.ndarray]:
    blocks: List[np.ndarray] = []
    for _ in range(count):
        block = silence(BLOCK)
        fill = source.read_into(block)
        blocks.append(block[: fill.frames])

    return blocks


def _played_out(source: LiveNoteSource) -> int:
    """The frames the source fills until a short fill ends it."""
    frames = 0
    for _ in range(ENOUGH_BLOCKS):
        fill = _read(source)
        frames += fill.frames
        if fill.frames < BLOCK:
            return frames

    raise AssertionError(f"the source played on past {ENOUGH_BLOCKS} blocks")


def _fresh(press: Strike) -> np.ndarray:
    """The first block a source pressed with ``press`` alone sounds."""
    source = LiveNoteSource(sustained=False, linger_seconds=LINGER_SECONDS)
    source.press(press)
    return _blocks(_begun(source), 1)[0]


def _midi(number: int) -> LiveKey:
    return LiveKey(keyboard=Keyboard.MIDI, number=number)


@pytest.fixture
def config() -> Config:
    return Config()


@pytest.fixture
def low(config: Config) -> Strike:
    return strike(Keyboard.MIDI, LOW, instrument_sound(held_instrument(), note=LOW, config=config))


@pytest.fixture
def high(config: Config) -> Strike:
    return strike(Keyboard.MIDI, HIGH, instrument_sound(held_instrument(), note=HIGH, config=config))


@pytest.fixture
def source() -> LiveNoteSource:
    return LiveNoteSource(sustained=False, linger_seconds=LINGER_SECONDS)


def _recording(config: Config) -> LiveSound:
    return sample_sound(short_sample(SAMPLE_FRAMES), step=0, config=config)


class TestTheFirstKey:
    """The key pressed before the stream opens sounds from the first block."""

    def test_a_key_pressed_before_the_stream_opens_sounds_at_once(self, source: LiveNoteSource, low: Strike) -> None:
        source.press(low)

        block = silence(BLOCK)
        fill = _begun(source).read_into(block)

        assert fill.frames == BLOCK
        assert np.any(block)

    def test_a_source_nothing_pressed_sounds_silence_and_ends(self, source: LiveNoteSource) -> None:
        blocks = _blocks(_begun(source), OPENING_BLOCKS)

        assert not any(np.any(block) for block in blocks)
        assert _played_out(source) + sum(len(block) for block in blocks) == LINGER_FRAMES


class TestTheSoundFollowsTheFront:
    """The press in front sounds as a fresh strike of it would, and a lift behind it changes nothing heard."""

    def test_a_new_press_strikes_its_note_afresh(self, source: LiveNoteSource, low: Strike, high: Strike) -> None:
        source.press(low)
        _blocks(_begun(source), OPENING_BLOCKS)

        source.press(high)

        np.testing.assert_array_equal(_blocks(source, 1)[0], _fresh(high))

    def test_lifting_the_front_strikes_the_key_still_held(
        self,
        source: LiveNoteSource,
        low: Strike,
        high: Strike,
    ) -> None:
        source.press(low)
        source.press(high)
        _blocks(_begun(source), OPENING_BLOCKS)

        source.release(high.key)

        np.testing.assert_array_equal(_blocks(source, 1)[0], _fresh(low))

    def test_lifting_a_key_behind_the_front_changes_nothing(self, config: Config) -> None:
        lifted, kept = (LiveNoteSource(sustained=False, linger_seconds=LINGER_SECONDS) for _ in range(2))
        for played in (lifted, kept):
            played.press(strike(Keyboard.MIDI, LOW, instrument_sound(held_instrument(), note=LOW, config=config)))
            played.press(strike(Keyboard.MIDI, HIGH, instrument_sound(held_instrument(), note=HIGH, config=config)))
            _blocks(_begun(played), OPENING_BLOCKS)

        lifted.release(_midi(LOW))

        np.testing.assert_array_equal(_blocks(lifted, OPENING_BLOCKS), _blocks(kept, OPENING_BLOCKS))
        lifted.release(_midi(HIGH))
        assert not np.array_equal(_blocks(lifted, 1)[0], _blocks(kept, 1)[0])


class TestHowLongTheSourcePlays:
    """The source sounds while a key is down or a note sounds, then lingers in silence and ends."""

    def test_a_key_held_past_its_recording_keeps_the_source(self, source: LiveNoteSource, config: Config) -> None:
        source.press(strike(Keyboard.MIDI, LOW, _recording(config)))

        blocks = _blocks(_begun(source), OPENING_BLOCKS + LINGER_FRAMES // BLOCK + 1)

        assert all(len(block) == BLOCK for block in blocks)
        assert np.any(blocks[0])
        assert not np.any(blocks[-1])

    def test_the_last_lift_lingers_then_ends(self, source: LiveNoteSource, low: Strike) -> None:
        source.press(low)
        _blocks(_begun(source), OPENING_BLOCKS)

        source.release(low.key)

        assert _played_out(source) == LINGER_FRAMES

    def test_a_press_during_the_linger_sounds_and_lingers_anew(
        self,
        source: LiveNoteSource,
        low: Strike,
        high: Strike,
    ) -> None:
        source.press(low)
        _blocks(_begun(source), OPENING_BLOCKS)
        source.release(low.key)
        _blocks(source, OPENING_BLOCKS)

        source.press(high)
        sounded = _blocks(source, 1)[0]
        source.release(high.key)

        np.testing.assert_array_equal(sounded, _fresh(high))
        assert _played_out(source) == LINGER_FRAMES

    def test_a_computer_key_lets_its_recording_play_to_its_end(self, config: Config) -> None:
        source = LiveNoteSource(sustained=False, linger_seconds=NO_LINGER)
        take = strike(Keyboard.COMPUTER, LOW, _recording(config))
        source.press(take)
        _begun(source)

        source.release(take.key)

        assert _played_out(source) == SAMPLE_FRAMES * OUTPUT_RATE // config.nes_frequency

    def test_a_midi_key_ends_its_recording_as_it_lifts(self, config: Config) -> None:
        source = LiveNoteSource(sustained=False, linger_seconds=NO_LINGER)
        take = strike(Keyboard.MIDI, LOW, _recording(config))
        source.press(take)
        _begun(source)

        source.release(take.key)

        assert _played_out(source) == 0

    def test_the_pedal_holds_a_lifted_note_until_it_comes_up(self, low: Strike) -> None:
        source = LiveNoteSource(sustained=True, linger_seconds=NO_LINGER)
        source.press(low)
        _blocks(_begun(source), 1)
        source.release(low.key)

        held_on = _blocks(source, OPENING_BLOCKS)
        source.pedal(False)

        assert all(len(block) == BLOCK and np.any(block) for block in held_on)
        assert _played_out(source) == 0

    def test_a_closed_source_comes_up_empty(self, source: LiveNoteSource, low: Strike) -> None:
        source.press(low)
        _begun(source)

        source.close()

        assert _read(source).frames == 0


class TestTheSettingsOfEachSound:
    """Each strike plays at the tick rate of the settings it carries, on generators built for them."""

    def test_a_recording_made_at_another_tick_rate_keeps_its_pace(self, config: Config) -> None:
        pal = config.with_library(nes_frequency=PAL_FREQUENCY)
        source = LiveNoteSource(sustained=False, linger_seconds=NO_LINGER)
        take = strike(Keyboard.COMPUTER, LOW, _recording(pal))
        source.press(take)
        source.release(take.key)

        assert _played_out(_begun(source)) == SAMPLE_FRAMES * OUTPUT_RATE // PAL_FREQUENCY

    def test_a_strike_under_other_settings_follows_them(self, config: Config, low: Strike) -> None:
        pal = config.with_library(nes_frequency=PAL_FREQUENCY)
        source = LiveNoteSource(sustained=False, linger_seconds=NO_LINGER)
        source.press(low)
        _blocks(_begun(source), OPENING_BLOCKS)
        source.release(low.key)

        take = strike(Keyboard.COMPUTER, HIGH, _recording(pal))
        source.press(take)
        source.release(take.key)

        assert _played_out(source) == SAMPLE_FRAMES * OUTPUT_RATE // PAL_FREQUENCY
