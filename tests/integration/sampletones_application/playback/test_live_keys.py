import threading
from typing import Final

from sampletones_application.logic.shared.live import Keyboard, LiveKey
from tests.integration.sampletones_application.playback.material import (
    HEARD,
    REALTIME,
    STEPPED,
    grant_and_hold,
    start_sounding,
)
from tests.integration.sampletones_application.playback.rig import PLAYED_KEY, EndCause, PlaybackRig, Sound
from tests.suite.audio.pacing import StepPacing
from tests.suite.base import BaseTestSuite

HIGHER_KEY: Final[int] = 67
HELD_WRITES: Final[int] = 2
EVERY_WRITE: Final[int] = 10_000
LINGER_FRAMES: Final[int] = 11_025
RACES: Final[int] = 30
RACE_SECONDS: Final[float] = 10.0


def _streams(rig: PlaybackRig) -> int:
    return len(rig.timeline.streams())


@STEPPED
class TestKeysShareAStream(BaseTestSuite):
    """Keys played one after another sound on one playback and one stream, a press during the linger included."""

    def test_a_key_pressed_during_the_linger_plays_on_the_open_stream(
        self, rig: PlaybackRig, steps: StepPacing
    ) -> None:
        rig.press(PLAYED_KEY, keyboard=Keyboard.MIDI)
        grant_and_hold(rig, steps, HELD_WRITES)
        rig.lift(PLAYED_KEY, keyboard=Keyboard.MIDI)

        rig.press(HIGHER_KEY, keyboard=Keyboard.MIDI)
        grant_and_hold(rig, steps, HELD_WRITES)
        rig.lift(HIGHER_KEY, keyboard=Keyboard.MIDI)
        steps.grant(EVERY_WRITE)
        rig.settle()

        assert _streams(rig) == 1
        assert rig.causes(Sound.KEYS) == [EndCause.FINISHED]

    def test_a_key_pressed_once_the_keys_ended_opens_a_stream(self, rig: PlaybackRig, steps: StepPacing) -> None:
        rig.press(PLAYED_KEY, keyboard=Keyboard.MIDI)
        rig.lift(PLAYED_KEY, keyboard=Keyboard.MIDI)
        steps.grant(EVERY_WRITE)
        rig.settle()

        rig.press(HIGHER_KEY, keyboard=Keyboard.MIDI)
        rig.lift(HIGHER_KEY, keyboard=Keyboard.MIDI)
        rig.settle()

        assert _streams(rig) == 2
        assert rig.causes(Sound.KEYS) == [EndCause.FINISHED, EndCause.FINISHED]


@REALTIME
class TestAKeyIsAPreview(BaseTestSuite):
    """Rule 1: a key takes the output from a preview, and the song holds it against a key."""

    def test_a_key_takes_the_output_from_a_preview(self, rig: PlaybackRig) -> None:
        start_sounding(rig, Sound.FILE)

        rig.press(PLAYED_KEY, keyboard=Keyboard.MIDI)
        rig.wait_for(lambda: bool(rig.ends(Sound.FILE)), what="the preview's end")

        assert rig.causes(Sound.FILE) == [EndCause.TAKEN]
        assert _streams(rig) == 2

    def test_a_key_while_the_song_plays_is_declined(self, rig: PlaybackRig) -> None:
        start_sounding(rig, Sound.SONG)
        streams = _streams(rig)

        rig.press(PLAYED_KEY, keyboard=Keyboard.MIDI)
        rig.drain()

        assert rig.engaged(Sound.SONG)
        assert _streams(rig) == streams
        assert rig.ends(Sound.KEYS) == []

    def test_a_key_once_the_song_stopped_sounds(self, rig: PlaybackRig) -> None:
        start_sounding(rig, Sound.SONG)
        rig.stop(Sound.SONG)
        rig.settle()
        streams = _streams(rig)

        rig.press(PLAYED_KEY, keyboard=Keyboard.MIDI)
        rig.wait_for(lambda: _streams(rig) == streams + 1, what="the key's stream")

        assert not rig.engaged(Sound.SONG)


@REALTIME
class TestALiftAfterAStop(BaseTestSuite):
    """Rule 6: Stop silences a held key, and lifting it afterwards sounds nothing."""

    def test_a_lift_after_stop_opens_nothing(self, rig: PlaybackRig) -> None:
        start_sounding(rig, Sound.KEYS)
        rig.stop_all()
        rig.settle()
        written = len(rig.timeline.written())

        rig.lift(PLAYED_KEY, keyboard=Keyboard.MIDI)
        rig.drain()

        assert _streams(rig) == 1
        assert len(rig.timeline.written()) == written
        assert rig.causes(Sound.KEYS) == [EndCause.STOPPED]

    def test_a_press_after_stop_sounds_again(self, rig: PlaybackRig) -> None:
        start_sounding(rig, Sound.KEYS)
        rig.stop_all()
        rig.settle()

        rig.press(PLAYED_KEY, keyboard=Keyboard.MIDI)
        rig.wait_for(lambda: _streams(rig) == 2, what="the key's second stream")
        rig.stop_all()
        rig.settle()

        assert rig.causes(Sound.KEYS) == [EndCause.STOPPED, EndCause.STOPPED]


class TestThePedal(BaseTestSuite):
    """The sustain pedal keeps a lifted key sounding until it comes up, and the keys end after their linger."""

    def test_a_key_lifted_under_the_pedal_sounds_on(self, rig: PlaybackRig) -> None:
        rig.pedal(True)
        rig.press(PLAYED_KEY, keyboard=Keyboard.MIDI)
        rig.lift(PLAYED_KEY, keyboard=Keyboard.MIDI)

        rig.wait_until_written(LINGER_FRAMES + HEARD)

        assert rig.ends(Sound.KEYS) == []
        rig.pedal(False)
        rig.settle()
        assert rig.causes(Sound.KEYS) == [EndCause.FINISHED]

    def test_a_key_lifted_without_the_pedal_ends_after_its_linger(self, rig: PlaybackRig) -> None:
        rig.press(PLAYED_KEY, keyboard=Keyboard.MIDI)
        rig.lift(PLAYED_KEY, keyboard=Keyboard.MIDI)

        rig.settle()

        assert rig.causes(Sound.KEYS) == [EndCause.FINISHED]
        assert len(rig.timeline.written()) < LINGER_FRAMES + HEARD


class TestKeysFromTheirOwnThread(BaseTestSuite):
    """Rules 2 and 3: keys a MIDI keyboard's thread plays while the reader presses Stop leave the device quiet."""

    def test_keys_racing_stop_leave_one_stream_at_a_time(self, rig: PlaybackRig) -> None:
        def play_keys() -> None:
            for race in range(RACES):
                number = PLAYED_KEY + race % 2
                rig.stack.keys.key_down(rig.stack.strike(Keyboard.MIDI, number))
                rig.stack.keys.key_up(LiveKey(keyboard=Keyboard.MIDI, number=number))

        keyboard = threading.Thread(target=play_keys, name="MidiKeyboard")
        keyboard.start()
        for _ in range(RACES):
            rig.stop_all()

        keyboard.join(timeout=RACE_SECONDS)
        rig.settle()

        assert not keyboard.is_alive()
        assert rig.timeline.most_streams_open() <= 1
        assert not rig.timeline.violations()
        assert not rig.stack.output.is_sounding
        assert rig.told == []
