from typing import Final

import pytest

from sampletones_application.logic.shared.live import HeldKeys, Keyboard, LiveKey, LiveSound, Strike
from sampletones_application.view_model.sequencer.voices import VoiceKind
from tests.suite.live import strike, unheard_sound

LOW: Final[int] = 60
MIDDLE: Final[int] = 64
HIGH: Final[int] = 67
UNPRESSED: Final[int] = 72


@pytest.fixture
def instrument() -> LiveSound:
    return unheard_sound(VoiceKind.INSTRUMENT)


@pytest.fixture
def recording() -> LiveSound:
    return unheard_sound(VoiceKind.SAMPLE)


@pytest.fixture
def held() -> HeldKeys:
    return HeldKeys(sustained=False)


@pytest.fixture
def pedalled() -> HeldKeys:
    return HeldKeys(sustained=True)


def _midi(number: int) -> LiveKey:
    return LiveKey(keyboard=Keyboard.MIDI, number=number)


class TestTheNewestKeyWins:
    """The newest press stands in front, and lifting a key behind it changes nothing heard."""

    def test_a_press_over_a_held_key_takes_the_front(self, held: HeldKeys, instrument: LiveSound) -> None:
        low, high = strike(Keyboard.MIDI, LOW, instrument), strike(Keyboard.MIDI, HIGH, instrument)

        held.press(low)
        held.press(high)

        assert held.front is high

    def test_lifting_a_key_behind_the_front_leaves_the_front(self, held: HeldKeys, instrument: LiveSound) -> None:
        low, high = strike(Keyboard.MIDI, LOW, instrument), strike(Keyboard.MIDI, HIGH, instrument)
        held.press(low)
        held.press(high)

        held.release(_midi(LOW))

        assert held.front is high
        held.release(_midi(HIGH))
        assert held.front is None

    def test_lifting_a_key_never_pressed_leaves_the_front(self, held: HeldKeys, instrument: LiveSound) -> None:
        low = strike(Keyboard.MIDI, LOW, instrument)
        held.press(low)

        held.release(_midi(UNPRESSED))

        assert held.front is low
        assert held.holds

    def test_a_key_pressed_again_strikes_again(self, held: HeldKeys, instrument: LiveSound) -> None:
        first, again = strike(Keyboard.MIDI, LOW, instrument), strike(Keyboard.MIDI, LOW, instrument)
        held.press(first)

        held.press(again)

        assert held.front is again
        held.release(_midi(LOW))
        assert held.front is None
        assert not held.holds


class TestReturningToAHeldKey:
    """Lifting the key in front returns to the most recent key still held, which strikes its own press again."""

    def test_lifting_the_front_returns_to_the_key_below(self, held: HeldKeys, instrument: LiveSound) -> None:
        low, high = strike(Keyboard.MIDI, LOW, instrument), strike(Keyboard.MIDI, HIGH, instrument)
        held.press(low)
        held.press(high)

        held.release(_midi(HIGH))

        assert held.front is low

    def test_the_return_skips_keys_lifted_meanwhile(self, held: HeldKeys, instrument: LiveSound) -> None:
        low = strike(Keyboard.MIDI, LOW, instrument)
        middle = strike(Keyboard.MIDI, MIDDLE, instrument)
        high = strike(Keyboard.MIDI, HIGH, instrument)
        for press in (low, middle, high):
            held.press(press)

        held.release(_midi(MIDDLE))
        held.release(_midi(HIGH))

        assert held.front is low

    def test_a_key_pressed_again_moves_above_the_rest(self, held: HeldKeys, instrument: LiveSound) -> None:
        low, high = strike(Keyboard.MIDI, LOW, instrument), strike(Keyboard.MIDI, HIGH, instrument)
        again = strike(Keyboard.MIDI, LOW, instrument)
        for press in (low, high, again):
            held.press(press)

        held.release(_midi(LOW))

        assert held.front is high

    def test_lifting_the_last_key_ends_the_note(self, held: HeldKeys, instrument: LiveSound) -> None:
        held.press(strike(Keyboard.MIDI, LOW, instrument))

        held.release(_midi(LOW))

        assert held.front is None
        assert not held.holds


class TestTheSustainPedal:
    """The pedal keeps the press in front sounding once its key lifts, and the lift takes effect as it comes up."""

    def test_a_key_lifted_under_the_pedal_sounds_on(self, pedalled: HeldKeys, instrument: LiveSound) -> None:
        low = strike(Keyboard.MIDI, LOW, instrument)
        pedalled.press(low)

        pedalled.release(_midi(LOW))

        assert pedalled.front is low
        assert not pedalled.holds

    def test_the_pedal_coming_up_ends_a_note_whose_key_lifted(self, pedalled: HeldKeys, instrument: LiveSound) -> None:
        pedalled.press(strike(Keyboard.MIDI, LOW, instrument))
        pedalled.release(_midi(LOW))

        pedalled.pedal(False)

        assert pedalled.front is None

    def test_the_pedal_coming_up_returns_to_a_key_still_held(self, held: HeldKeys, instrument: LiveSound) -> None:
        low, high = strike(Keyboard.MIDI, LOW, instrument), strike(Keyboard.MIDI, HIGH, instrument)
        held.press(low)
        held.press(high)
        held.pedal(True)
        held.release(_midi(HIGH))
        assert held.front is high

        held.pedal(False)

        assert held.front is low

    def test_the_pedal_coming_up_leaves_a_key_still_down(self, pedalled: HeldKeys, instrument: LiveSound) -> None:
        low = strike(Keyboard.MIDI, LOW, instrument)
        pedalled.press(low)

        pedalled.pedal(False)

        assert pedalled.front is low

    def test_a_new_press_under_the_pedal_takes_the_front(self, pedalled: HeldKeys, instrument: LiveSound) -> None:
        low, high = strike(Keyboard.MIDI, LOW, instrument), strike(Keyboard.MIDI, HIGH, instrument)
        pedalled.press(low)
        pedalled.release(_midi(LOW))

        pedalled.press(high)
        pedalled.release(_midi(HIGH))

        assert pedalled.front is high
        pedalled.pedal(False)
        assert pedalled.front is None

    def test_a_key_pressed_again_under_the_pedal_strikes_again(self, pedalled: HeldKeys, instrument: LiveSound) -> None:
        first, again = strike(Keyboard.MIDI, LOW, instrument), strike(Keyboard.MIDI, LOW, instrument)
        pedalled.press(first)
        pedalled.release(_midi(LOW))

        pedalled.press(again)

        assert pedalled.front is again


class TestARecordingOnEachKeyboard:
    """A computer key plays a recording to its end, a MIDI key ends it as it lifts, and the two keyboards hold
    their keys apart."""

    def test_a_computer_key_lifted_leaves_its_recording_in_front(self, held: HeldKeys, recording: LiveSound) -> None:
        take = strike(Keyboard.COMPUTER, LOW, recording)
        held.press(take)

        held.release(LiveKey(keyboard=Keyboard.COMPUTER, number=LOW))

        assert held.front is take
        assert not held.holds

    def test_a_midi_key_lifted_ends_its_recording(self, held: HeldKeys, recording: LiveSound) -> None:
        held.press(strike(Keyboard.MIDI, LOW, recording))

        held.release(_midi(LOW))

        assert held.front is None

    def test_a_midi_lift_leaves_a_computer_keys_recording(self, held: HeldKeys, recording: LiveSound) -> None:
        held.press(strike(Keyboard.MIDI, LOW, recording))
        take = strike(Keyboard.COMPUTER, LOW, recording)
        held.press(take)

        held.release(_midi(LOW))

        assert held.front is take
        held.release(LiveKey(keyboard=Keyboard.COMPUTER, number=LOW))
        assert held.front is take

    def test_a_recording_played_through_ignores_the_pedal(self, held: HeldKeys, recording: LiveSound) -> None:
        take = strike(Keyboard.COMPUTER, LOW, recording)
        held.pedal(True)
        held.press(take)
        held.release(LiveKey(keyboard=Keyboard.COMPUTER, number=LOW))

        held.pedal(False)

        assert held.front is take

    def test_a_new_press_cuts_a_recording_played_through(self, held: HeldKeys, recording: LiveSound) -> None:
        held.press(strike(Keyboard.COMPUTER, LOW, recording))
        held.release(LiveKey(keyboard=Keyboard.COMPUTER, number=LOW))
        high: Strike = strike(Keyboard.COMPUTER, HIGH, recording)

        held.press(high)

        assert held.front is high
