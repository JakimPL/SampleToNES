from typing import Final, List

import pytest

from sampletones_application.logic.shared.live import Keyboard, LiveKeysLogic, LiveNoteSource, Strike
from sampletones_application.logic.shared.playback_priority import PlaybackPriority
from sampletones_application.logic.shared.preview_player import PreviewPlayer
from sampletones_core.audio import silence
from sampletones_core.audio.output import EndCause, Ending, Playback
from sampletones_core.configs import Config
from sampletones_shared.exceptions import NoOutputDeviceError, PlaybackError
from sampletones_shared.types.callback import VoidCallback
from tests.suite.audio.output import FakeAudioOutput
from tests.suite.live import held_instrument, instrument_sound, strike

OUTPUT_RATE: Final[int] = 44100
BLOCK: Final[int] = 1024
LINGER_SECONDS: Final[float] = 0.05
ENOUGH_BLOCKS: Final[int] = 40
LOW: Final[int] = 60
HIGH: Final[int] = 67
NO_DEVICE: Final[str] = "No audio output device is in force"
DEVICE_FAILURE: Final[str] = "The device failed"


class Told:
    """What the keys post to the render thread, and what reaches the failure report once the posts run."""

    def __init__(self) -> None:
        self.posted: List[VoidCallback] = []
        self.failures: List[Exception] = []

    def run_posted(self) -> None:
        posted, self.posted = self.posted, []
        for delivery in posted:
            delivery()


@pytest.fixture
def output() -> FakeAudioOutput:
    return FakeAudioOutput()


@pytest.fixture
def previews(output: FakeAudioOutput) -> PreviewPlayer:
    return PreviewPlayer(output)


@pytest.fixture
def told() -> Told:
    return Told()


@pytest.fixture
def keys(previews: PreviewPlayer, told: Told) -> LiveKeysLogic:
    return LiveKeysLogic(previews, post=told.posted.append, failed=told.failures.append, linger_seconds=LINGER_SECONDS)


@pytest.fixture
def low() -> Strike:
    return strike(Keyboard.MIDI, LOW, instrument_sound(held_instrument(), note=LOW, config=Config()))


@pytest.fixture
def high() -> Strike:
    return strike(Keyboard.MIDI, HIGH, instrument_sound(held_instrument(), note=HIGH, config=Config()))


def _unexpected(error: Exception) -> None:
    raise AssertionError(f"a live source told a failure between reads: {error}")


def _source(output: FakeAudioOutput, playback: Playback[None]) -> LiveNoteSource:
    source = output.claim(playback).source
    assert isinstance(source, LiveNoteSource)
    return source


def _ends(source: LiveNoteSource) -> bool:
    """Whether the source, begun now, ends within :data:`ENOUGH_BLOCKS`, which it does once nothing holds it."""
    source.begin(OUTPUT_RATE, _unexpected)
    return any(source.read_into(silence(BLOCK)).frames < BLOCK for _ in range(ENOUGH_BLOCKS))


class TestAPressClaimsTheOutput:
    """A press claims the output as a preview where no live playback holds it, and reaches the one holding it."""

    def test_a_press_claims_a_preview_stop_reaches(
        self,
        keys: LiveKeysLogic,
        output: FakeAudioOutput,
        previews: PreviewPlayer,
        low: Strike,
    ) -> None:
        keys.key_down(low)
        claim = output.claim(output.latest)

        previews.stop()

        assert claim.rank == PlaybackPriority.PREVIEW
        assert claim.stopped

    def test_keys_played_one_after_another_share_one_playback(
        self,
        keys: LiveKeysLogic,
        output: FakeAudioOutput,
        low: Strike,
        high: Strike,
    ) -> None:
        keys.key_down(low)
        keys.key_up(low.key)

        keys.key_down(high)

        assert len(output.playbacks) == 1

    def test_a_press_after_the_playback_ended_claims_anew(
        self,
        keys: LiveKeysLogic,
        output: FakeAudioOutput,
        low: Strike,
        high: Strike,
    ) -> None:
        keys.key_down(low)
        output.end(output.latest, Ending.of(EndCause.TAKEN))

        keys.key_down(high)

        assert len(output.playbacks) == 2
        assert output.claim(output.latest).engaged

    def test_a_declined_press_leaves_nothing_for_its_lift(
        self,
        keys: LiveKeysLogic,
        output: FakeAudioOutput,
        low: Strike,
    ) -> None:
        output.declining = True
        keys.key_down(low)
        output.declining = False

        keys.key_up(low.key)

        assert not output.playbacks
        keys.key_down(low)
        assert len(output.playbacks) == 1


class TestALiftReachesThePlaybackHoldingTheOutput:
    """A lift reaches the playback holding the output, and a playback stopped or taken hears nothing more."""

    def test_a_lift_reaches_the_playback_holding_the_output(
        self,
        keys: LiveKeysLogic,
        output: FakeAudioOutput,
        low: Strike,
    ) -> None:
        keys.key_down(low)

        keys.key_up(low.key)

        assert _ends(_source(output, output.latest))

    def test_a_lift_after_a_stop_reaches_nothing(
        self,
        keys: LiveKeysLogic,
        output: FakeAudioOutput,
        previews: PreviewPlayer,
        low: Strike,
    ) -> None:
        keys.key_down(low)
        stopped = output.latest
        previews.stop()

        keys.key_up(low.key)

        assert not _ends(_source(output, stopped))
        assert len(output.playbacks) == 1

    def test_a_lift_after_a_takeover_reaches_nothing(
        self,
        keys: LiveKeysLogic,
        output: FakeAudioOutput,
        low: Strike,
    ) -> None:
        keys.key_down(low)
        taken = output.latest
        output.end(taken, Ending.of(EndCause.TAKEN))

        keys.key_up(low.key)

        assert not _ends(_source(output, taken))
        assert len(output.playbacks) == 1


class TestThePedal:
    """The pedal's state outlives a playback, so a press after it went down meets it held."""

    def test_a_press_on_a_new_playback_meets_the_pedal_down(
        self,
        keys: LiveKeysLogic,
        output: FakeAudioOutput,
        low: Strike,
        high: Strike,
    ) -> None:
        keys.pedal(True)
        keys.key_down(low)
        output.end(output.latest, Ending.of(EndCause.TAKEN))
        keys.key_down(high)

        keys.key_up(high.key)

        assert not _ends(_source(output, output.latest))

    def test_the_pedal_coming_up_lets_the_note_go(
        self,
        keys: LiveKeysLogic,
        output: FakeAudioOutput,
        low: Strike,
    ) -> None:
        keys.pedal(True)
        keys.key_down(low)
        keys.key_up(low.key)

        keys.pedal(False)

        assert _ends(_source(output, output.latest))

    def test_silence_keeps_the_pedal_down(
        self,
        keys: LiveKeysLogic,
        output: FakeAudioOutput,
        low: Strike,
        high: Strike,
    ) -> None:
        keys.pedal(True)
        keys.key_down(low)
        silenced = output.claim(output.latest)

        keys.silence()
        keys.key_down(high)
        keys.key_up(high.key)

        assert silenced.stopped
        assert not _ends(_source(output, output.latest))


class TestFailures:
    """A failure is told to the render thread once: a claim refused for want of a device, or a playback failing."""

    def test_a_refused_claim_is_posted(
        self, keys: LiveKeysLogic, output: FakeAudioOutput, told: Told, low: Strike
    ) -> None:
        refusal = NoOutputDeviceError(NO_DEVICE)
        output.refusal = refusal

        keys.key_down(low)

        assert not told.failures
        told.run_posted()
        assert told.failures == [refusal]

    def test_a_playback_failing_is_told(
        self, keys: LiveKeysLogic, output: FakeAudioOutput, told: Told, low: Strike
    ) -> None:
        failure = PlaybackError(DEVICE_FAILURE)
        keys.key_down(low)

        output.end(output.latest, Ending.failure(failure))

        assert told.failures == [failure]

    def test_a_playback_let_go_fails_unheard(
        self,
        keys: LiveKeysLogic,
        output: FakeAudioOutput,
        told: Told,
        low: Strike,
    ) -> None:
        keys.key_down(low)
        silenced = output.latest
        keys.silence()

        output.end(silenced, Ending.failure(PlaybackError(DEVICE_FAILURE)))

        assert not told.failures
        assert not told.posted
