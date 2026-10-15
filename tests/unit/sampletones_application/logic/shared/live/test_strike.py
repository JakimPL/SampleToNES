import pytest

from sampletones_application.logic.shared.live import Keyboard, release_ends_note
from sampletones_application.view_model.sequencer.voices import VoiceKind


class TestWhatALiftEnds:
    """A lift ends an instrument's note from either keyboard, and a recording's from a MIDI key alone."""

    @pytest.mark.parametrize("keyboard", list(Keyboard))
    def test_an_instrument_ends_as_its_key_lifts_on_either_keyboard(self, keyboard: Keyboard) -> None:
        assert release_ends_note(keyboard, VoiceKind.INSTRUMENT)

    def test_a_midi_key_ends_a_recording_as_it_lifts(self) -> None:
        assert release_ends_note(Keyboard.MIDI, VoiceKind.SAMPLE)

    def test_a_computer_key_lets_a_recording_play_to_its_end(self) -> None:
        assert not release_ends_note(Keyboard.COMPUTER, VoiceKind.SAMPLE)
        assert release_ends_note(Keyboard.COMPUTER, VoiceKind.INSTRUMENT)
