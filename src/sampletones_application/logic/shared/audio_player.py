from functools import partial
from typing import Callable, Optional

from sampletones_application.logic.shared.playback_priority import PlaybackPriority
from sampletones_application.view_model.shared.audio_data import AudioData
from sampletones_core.audio.output import AudioOutput, BufferSource, Ending, Playback, unity_gain
from sampletones_core.constants.audio import DEFAULT_SAMPLE_RATE, START_OF_AUDIO
from sampletones_shared.types.callback import VoidCallback
from sampletones_shared.utils.callbacks import CallbackMixin


class AudioPlayer(CallbackMixin):
    """Plays the buffer a tab holds, the reconstruction or the instruction it shows, at the reader's request.

    The player holds the playback it started and is that playback's listener, so a report of an older one
    finds a newer one held and changes nothing. The mark follows the positions the device took, and a seek
    draws the sample it moved to at once, which the positions then follow. A playback whose end is decided
    refuses a seek, and the click then starts a new one from the sample clicked. The player tells a failure
    of its playback through ``on_error`` and moves its mark off once the playback ends.
    """

    def __init__(self, output: AudioOutput) -> None:
        self._output = output
        self.audio_data: AudioData = AudioData.empty(DEFAULT_SAMPLE_RATE)
        self._playback: Optional[Playback[int]] = None
        self._source: Optional[BufferSource] = None
        self._position: int = START_OF_AUDIO

        self.on_position_changed: Optional[Callable[[int], None]] = None
        self.on_change_audio_state: Optional[VoidCallback] = None
        self.on_error: Optional[Callable[[Exception], None]] = None

    @property
    def current_position(self) -> int:
        """Where this player's playback stands, sounding or held paused, as the device last reported it."""
        return self._position

    @property
    def is_playing(self) -> bool:
        """Whether this player's playback holds the output, sounding or held paused."""
        return self._playback is not None and self._playback.engaged

    @property
    def is_paused(self) -> bool:
        return self._playback is not None and self._playback.engaged and self._playback.paused

    def load_audio_data(self, audio_data: AudioData) -> None:
        """Takes the audio the tab now shows, which a playback under way plays on from the moment it reached."""
        self.audio_data = audio_data
        if self._playback is not None and self._source is not None:
            self._playback.command(partial(self._source.replace, audio_data.sample, sample_rate=audio_data.sample_rate))

        self._notify_audio_state_changed()

    def clear_audio(self) -> None:
        self.stop()
        self.audio_data = AudioData.empty(self.audio_data.sample_rate)

    def seek(self, position: int) -> bool:
        """Moves this player's playback to a sample, whether it sounds or stands paused.

        The device reports positions as it plays, and a paused one plays nothing, so the player draws the
        sample it moved to, which carries the mark there during a pause as well.

        Args:
            position: The sample to move to, clamped to the audio.

        Returns:
            bool: Whether this player's playback still played, and so moved.
        """
        if self._playback is None or self._source is None:
            return False

        target = self._clamped(position)
        if not self._playback.command(partial(self._source.seek, target)):
            return False

        self._position = target
        self.call(self.on_position_changed, target)
        return True

    def play(self, *, start: int) -> None:
        """Takes the output and sounds the loaded audio from a sample.

        Args:
            start: The sample playback begins at, clamped to the audio.

        Raises:
            NoOutputDeviceError: If no output device is in force.
        """
        if not self.audio_data.is_loaded():
            self._notify_audio_state_changed()
            return

        self._let_go()
        source = BufferSource(self.audio_data.sample, sample_rate=self.audio_data.sample_rate, start=start)
        playback = self._output.play(source, rank=PlaybackPriority.NORMAL, listener=self, gain=unity_gain)
        if playback is not None:
            self._playback, self._source = playback, source
            self._position = self._clamped(start)

        self._notify_audio_state_changed()

    def pause(self) -> None:
        if self._playback is not None:
            self._playback.pause()

        self._notify_audio_state_changed()

    def resume(self) -> None:
        if self._playback is not None:
            self._playback.resume()

        self._notify_audio_state_changed()

    def stop(self) -> None:
        self._let_go()
        self.call(self.on_position_changed, START_OF_AUDIO)
        self._notify_audio_state_changed()

    def positioned(self, playback: Playback[int], report: int) -> None:
        if playback is not self._playback:
            return

        self._position = report
        self.call(self.on_position_changed, report)

    def ended(self, playback: Playback[int], ending: Ending) -> None:
        """Moves the mark off once this player's playback ends, telling the failure where it failed."""
        if playback is not self._playback:
            return

        self._playback, self._source = None, None
        self._position = START_OF_AUDIO
        self.call(self.on_position_changed, START_OF_AUDIO)
        if ending.error is not None:
            self.call(self.on_error, ending.error)

        self._notify_audio_state_changed()

    def _let_go(self) -> None:
        """Stops the playback held and lets it go, so its end report finds nothing held."""
        playback, self._playback, self._source = self._playback, None, None
        self._position = START_OF_AUDIO
        if playback is not None:
            playback.stop()

    def _clamped(self, position: int) -> int:
        return max(START_OF_AUDIO, min(position, self.audio_data.samples))

    def _notify_audio_state_changed(self) -> None:
        self.call(self.on_change_audio_state)
