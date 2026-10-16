from typing import Dict, List, Optional

from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.sequencer.channels import SequencerChannelsLogic
from sampletones_application.logic.sequencer.tracker.tracker import SequencerTrackerLogic
from sampletones_application.logic.shared.live import LiveKey, LiveKeysLogic, LiveSound, Strike
from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import MAX_VOLUME
from sampletones_core.project.patterns.pitch import RowPitch
from sampletones_core.project.voices.note_on import NoteOn


class SequencerKeys:
    """Sounds the row a key entered in the tracker, for as long as the key is down.

    A key entering a note writes the row first, on the render thread, and then sounds the row as the project
    now holds it, so what is heard is what the song plays there: the voice the row names on each channel the
    cell reaches, at the row's pitch, and at its volume or the full level where it states none. A row naming
    no voice moves a note it did not start, so it sounds nothing, and neither does a channel the reader
    silenced. The sound is a key played live, so it yields to the song and to playback the reader asked for.
    """

    def __init__(
        self,
        tracker: SequencerTrackerLogic,
        channels: SequencerChannelsLogic,
        project_controller: ProjectController,
        live_keys: LiveKeysLogic,
    ) -> None:
        self._tracker = tracker
        self._channels = channels
        self._controller = project_controller
        self._live_keys = live_keys

    def strike(self, key: LiveKey, row_index: int, channel: Optional[ChannelName]) -> None:
        """Sounds the row ``key`` entered a note on, in the cell of ``channel``, ``None`` for the sample column."""
        sound = self._row_sound(row_index, channel)
        if sound is not None:
            self._live_keys.key_down(Strike(key=key, sound=sound, follower=None))

    def lift(self, key: LiveKey) -> None:
        self._live_keys.key_up(key)

    def _row_sound(self, row_index: int, channel: Optional[ChannelName]) -> Optional[LiveSound]:
        """What the row starts on the channels the cell reaches and the reader hears, as one voice."""
        starts = self._starts(row_index, channel)
        if not starts:
            return None

        voice_id = next(iter(starts.values())).voice_id
        voice = self._controller.project.voices.get(voice_id)
        if voice is None:
            return None

        pitches: Dict[ChannelName, RowPitch] = {}
        levels: Dict[ChannelName, int] = {}
        for name, note_on in starts.items():
            row = self._tracker.row(name, row_index)
            if note_on.voice_id != voice_id or row is None or row.pitch is None:
                continue

            pitches[name] = row.pitch
            levels[name] = MAX_VOLUME if row.volume is None else row.volume

        sound = LiveSound.of_voice(
            voice.snapshot(),
            pitches=pitches,
            levels=levels,
            config=self._controller.project.settings.synthesis_config(),
        )
        return sound if sound.channels else None

    def _starts(self, row_index: int, channel: Optional[ChannelName]) -> Dict[ChannelName, NoteOn]:
        """The note each channel the cell reaches starts at the row, on the channels the reader hears."""
        heard = self._channels.active_channels
        starts: Dict[ChannelName, NoteOn] = {}
        for name in self._reached(row_index, channel):
            row = self._tracker.row(name, row_index)
            if name in heard and row is not None and isinstance(row.command, NoteOn):
                starts[name] = row.command

        return starts

    def _reached(self, row_index: int, channel: Optional[ChannelName]) -> List[ChannelName]:
        """The channels a cell's note reaches: its own, or the ones a sample plays on for the sample column."""
        if channel is not None:
            return [channel]

        return self._tracker.relevant_channels(row_index)
