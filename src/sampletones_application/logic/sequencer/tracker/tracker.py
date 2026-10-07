from typing import Callable, Dict, FrozenSet, List, Mapping, Optional, Set

from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.view_model.sequencer.kind import (
    voice_kind,
)
from sampletones_application.view_model.sequencer.settings import (
    SequencerSettingsViewModel,
)
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_application.view_model.sequencer.tracker import (
    SequencerCellViewModel,
    SequencerRowViewModel,
    SequencerTrackerViewModel,
)
from sampletones_application.view_model.sequencer.voices import VoiceKind
from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import MAX_VOLUME
from sampletones_core.project.patterns.pattern import Pattern
from sampletones_core.project.patterns.pitch import Note, RowPitch, Step, note_for_channel, shifted_pitch
from sampletones_core.project.patterns.row import NoteCommand, Row
from sampletones_core.project.voices.note_off import NoteOff
from sampletones_core.project.voices.note_on import NoteOn
from sampletones_core.project.voices.sample import Sample
from sampletones_core.project.voices.voice import VoiceUnion, voice_channels
from sampletones_core.utils.display import (
    display_command,
    display_id,
    display_pitch,
    display_volume,
)
from sampletones_shared.utils.callbacks import CallbackMixin

_EMPTY_CELL = SequencerCellViewModel(
    voice=display_id(None),
    transpose=display_pitch(None),
    volume=display_volume(None),
    kind=None,
    pitch=None,
    level=None,
    command=None,
)


class SequencerTrackerLogic(CallbackMixin):
    """Builds the tracker grid and module-options view models from the project.

    Holds the only piece of grid-local UI state, the visible order frame, and
    translates raw panel events into :class:`ProjectController` mutations. The
    controller's change events are wired (by the coordinator) back to the push
    methods here, so a single mutation round-trips into a refreshed view.

    Cell-level edits take an ``Optional[ChannelName]`` naming the column they
    address: a channel reaches that channel alone, while ``None`` addresses the
    sample column and spreads the edit over the channels that column governs.
    """

    def __init__(self, project_controller: ProjectController) -> None:
        self._controller = project_controller
        self._frame_index: int = 0

        self.on_settings_changed: Optional[Callable[[SequencerSettingsViewModel], None]] = None
        self.on_tracker_changed: Optional[Callable[[SequencerTrackerViewModel], None]] = None
        self.on_frame_changed: Optional[Callable[[int], None]] = None

    @property
    def settings(self) -> SequencerSettingsViewModel:
        project = self._controller.project
        project_settings = project.settings
        return SequencerSettingsViewModel(
            nes_frequency=project_settings.nes_frequency,
            tempo=project_settings.tempo,
            speed=project_settings.speed,
            rows_per_pattern=project.song.rows_per_pattern,
            first_highlight=project_settings.first_highlight,
            second_highlight=project_settings.second_highlight,
        )

    def build_grid(self) -> SequencerTrackerViewModel:
        song = self._controller.project.song
        frame_count = song.order_length()
        frame_index = self._clamp_frame(frame_count)

        patterns = self._frame_patterns()
        carried: Dict[ChannelName, Optional[VoiceUnion]] = {channel: None for channel in ChannelName.items()}
        rows = tuple(self._build_row(index, patterns, carried) for index in range(self.frame_row_count()))
        return SequencerTrackerViewModel(
            frame_index=frame_index,
            frame_count=frame_count,
            rows=rows,
        )

    def frame_row_count(self) -> int:
        """Rows the current frame holds, the height a whole-frame edit spans.

        A frame is as tall as its longest pattern. Empty (None) slots contribute no
        pattern, so a frame whose channels are all empty falls back to
        ``rows_per_pattern`` blank rows — keeping the frame editable so the first
        keystroke can auto-create a pattern for that channel. Until the order holds
        its first frame, the count is zero.
        """
        song = self._controller.project.song
        if song.order_length() == 0:
            return 0

        lengths = [pattern.length for pattern in self._frame_patterns().values()]
        if lengths:
            return max(lengths)

        return song.rows_per_pattern

    def _frame_patterns(self) -> Dict[ChannelName, Pattern]:
        """The patterns the current frame's channels point at.

        A channel contributes an entry once its slot names a pattern the song holds,
        so the result covers exactly the channels carrying content at this frame.
        """
        song = self._controller.project.song
        if self._frame_index >= song.order_length():
            return {}

        patterns: Dict[ChannelName, Pattern] = {}
        for channel in ChannelName.items():
            index = song.order[self._frame_index].get(channel)
            pattern = song.pattern(channel, index) if index is not None else None
            if pattern is not None:
                patterns[channel] = pattern

        return patterns

    def push_settings(self) -> None:
        self.call(self.on_settings_changed, self.settings)

    def push_tracker(self) -> None:
        view_model = self.build_grid()
        self.call(self.on_tracker_changed, view_model)
        self.call(self.on_frame_changed, view_model.frame_index)

    def refresh(self) -> None:
        self.push_settings()
        self.push_tracker()

    def set_nes_frequency(self, nes_frequency: int) -> None:
        self._controller.set_nes_frequency(nes_frequency)

    def set_rows_per_pattern(self, rows_per_pattern: int) -> None:
        self._controller.set_rows_per_pattern(rows_per_pattern)

    def set_tempo(self, tempo: int) -> None:
        self._controller.set_tempo(tempo)

    def set_speed(self, speed: int) -> None:
        self._controller.set_speed(speed)

    def clear_cell(
        self,
        row_index: int,
        channel: Optional[ChannelName],
    ) -> None:
        if channel is None:
            self.clear_all_channels(row_index)
        else:
            self.clear_row(channel, row_index)

    def clear_cell_subcolumn(
        self,
        row_index: int,
        channel: Optional[ChannelName],
        subcolumn: SubColumn,
    ) -> None:
        """Empties one subcolumn of a cell.

        From the sample column the voice slot reaches every channel, since the sample
        it names is the row's whole note, while transpose and volume reach the
        channels a sample plays on at the row, as :meth:`relevant_channels` reads them.
        """
        voice = subcolumn is SubColumn.VOICE
        pitch = subcolumn is SubColumn.TRANSPOSE
        volume = subcolumn is SubColumn.VOLUME
        if channel is not None:
            self.clear_subcolumn(
                channel,
                row_index,
                voice=voice,
                pitch=pitch,
                volume=volume,
            )
        elif voice:
            self.clear_subcolumn_all_generators(row_index, voice=True)
        else:
            self.clear_sample_subcolumn(
                row_index,
                pitch=pitch,
                volume=volume,
            )

    def write_cell(
        self,
        row_index: int,
        channel: Optional[ChannelName],
        voice_id: Optional[str],
        pitch: Optional[RowPitch],
        volume: Optional[int],
    ) -> None:
        """Writes the values a cell edit carries, keeping the rest of the cell as it stands.

        A voice is placed first, and the pitch and the volume reach the cell after it, so a pitch
        typed with a marked voice lands on the channels the voice was just placed on: in the sample
        column the sample spreads over its channels, then the pitch reaches them.
        """
        if voice_id is not None:
            self.place_note(row_index, channel, voice_id)

        if pitch is not None or volume is not None:
            self.set_cell_subcolumn(
                row_index,
                channel,
                pitch=pitch,
                volume=volume,
            )

    def place_note(
        self,
        row_index: int,
        channel: Optional[ChannelName],
        voice_id: str,
    ) -> None:
        """Places a voice on the cell a column and a row name, where that column takes it.

        Every route that names a voice for a cell arrives here — a typed number, a menu item and a
        pasted block alike — so the sample column's rule is asked once and each of them follows it.
        """
        if channel is None:
            if self.places_in_sample_column(voice_id):
                self.set_row_sample(row_index, voice_id)
        else:
            self.set_row(
                channel,
                row_index,
                command=NoteOn(voice_id=voice_id),
            )

    def places_in_sample_column(self, voice_id: str) -> bool:
        """Whether the sample column takes the voice an id names.

        The column spreads a voice over the channels it covers, which a recording states for
        itself, so it answers for a sample the project holds and stands by for anything else.
        """
        voice = self._controller.project.voices.get(voice_id)
        if voice is None:
            return False

        return voice_kind(voice).places_across_channels

    def cut_note(
        self,
        row_index: int,
        channel: Optional[ChannelName],
    ) -> None:
        if channel is None:
            self.set_note_off_all_generators(row_index)
        else:
            self.set_note_off(channel, row_index)

    def set_cell_subcolumn(
        self,
        row_index: int,
        channel: Optional[ChannelName],
        *,
        pitch: Optional[RowPitch] = None,
        volume: Optional[int] = None,
    ) -> None:
        if channel is None:
            self.set_sample_subcolumn(
                row_index,
                pitch=pitch,
                volume=volume,
            )
        else:
            self.set_row(
                channel,
                row_index,
                pitch=pitch,
                volume=volume,
            )

    def set_row(
        self,
        channel: ChannelName,
        row_index: int,
        *,
        command: Optional[NoteCommand] = None,
        pitch: Optional[RowPitch] = None,
        volume: Optional[int] = None,
    ) -> None:
        pattern_index = self._pattern_index_at_frame(channel)
        if pattern_index is None:
            pattern_index = self._create_frame_pattern(channel)

        if pattern_index is None:
            return

        self._controller.update_row(
            channel,
            pattern_index,
            row_index,
            command=command,
            pitch=pitch,
            volume=volume,
        )

    def clear_row(self, channel: ChannelName, row_index: int) -> None:
        pattern_index = self._pattern_index_at_frame(channel)
        if pattern_index is None:
            return

        self._controller.clear_row(channel, pattern_index, row_index)

    def clear_subcolumn(
        self,
        channel: ChannelName,
        row_index: int,
        *,
        voice: bool = False,
        pitch: bool = False,
        volume: bool = False,
    ) -> None:
        pattern_index = self._pattern_index_at_frame(channel)
        if pattern_index is None:
            return

        self._controller.clear_row(
            channel,
            pattern_index,
            row_index,
            voice=voice,
            pitch=pitch,
            volume=volume,
        )

    def clear_all_channels(self, row_index: int) -> None:
        for channel in ChannelName.items():
            self.clear_row(channel, row_index)

    def clear_subcolumn_all_generators(
        self,
        row_index: int,
        *,
        voice: bool = False,
        pitch: bool = False,
        volume: bool = False,
    ) -> None:
        for channel in ChannelName.items():
            self.clear_subcolumn(
                channel,
                row_index,
                voice=voice,
                pitch=pitch,
                volume=volume,
            )

    def set_row_sample(
        self,
        row_index: int,
        voice_id: Optional[str],
    ) -> None:
        """Places a sample across the channels its reconstruction uses.

        The sample column is authoritative: the sample is written to every channel it covers, and
        the remaining channels on that row are cleared so the row plays exactly that sample.
        An empty voice id wipes the whole row.

        The column speaks for samples, which carry a slice per channel. An instrument sounds
        on whichever channel the reader names it in, so it is placed in a channel column and this
        one leaves the row as it stands.
        """
        if voice_id is None:
            self.clear_all_channels(row_index)
            return

        sample = self._controller.project.voices.get(voice_id)
        if not isinstance(sample, Sample):
            return

        used = self._used_generators(sample)
        for channel in ChannelName.items():
            if channel in used:
                self.set_row(
                    channel,
                    row_index,
                    command=NoteOn(voice_id=voice_id),
                )
            else:
                self.clear_row(channel, row_index)

    def carried_voice(
        self,
        channel: ChannelName,
        row_index: int,
    ) -> Optional[VoiceUnion]:
        """The voice a channel is carrying at a row of the frame shown.

        A row may bend a note it did not start, so the answer is found by reading down the frame's
        rows to this one, the way the grid reads its pitch column.
        """
        pattern_index = self._pattern_index_at_frame(channel)
        pattern = self._controller.project.song.pattern(channel, pattern_index) if pattern_index is not None else None
        if pattern is None:
            return None

        carried: Optional[VoiceUnion] = None
        for row in pattern.rows[: row_index + 1]:
            carried = self._carried_voice(row, carried)

        return carried

    def set_note_off(self, channel: ChannelName, row_index: int) -> None:
        """Writes a note-off into one channel's cell, materializing the pattern if needed."""
        self.set_row(channel, row_index, command=NoteOff())

    def set_note_off_all_generators(self, row_index: int) -> None:
        """Cuts every channel at this row, the sample-column counterpart of :meth:`set_note_off`."""
        for channel in ChannelName.items():
            self.set_note_off(channel, row_index)

    def set_sample_subcolumn(
        self,
        row_index: int,
        *,
        pitch: Optional[RowPitch] = None,
        volume: Optional[int] = None,
    ) -> None:
        """Writes a pitch or a volume to the channels a sample plays on at the row.

        A row placing a sample reaches that sample's whole span, and a row below it reaches
        the channels the sample is still playing on, as :meth:`relevant_channels` reads them.
        A row where no sample plays takes nothing, and gains no pattern. A note reaches each
        channel as that channel names it, so the noise channel takes the period the pitch names.
        """
        for channel in self._subcolumn_generators(row_index):
            self.set_row(
                channel,
                row_index,
                pitch=self._channel_pitch(channel, pitch),
                volume=volume,
            )

    @staticmethod
    def _channel_pitch(
        channel: ChannelName,
        pitch: Optional[RowPitch],
    ) -> Optional[RowPitch]:
        """The pitch one channel takes from the sample column: a note as the channel names it, a step as it stands."""
        match pitch:
            case Note():
                return note_for_channel(channel, pitch.value)
            case _:
                return pitch

    def clear_sample_subcolumn(
        self,
        row_index: int,
        *,
        pitch: bool = False,
        volume: bool = False,
    ) -> None:
        for channel in self._subcolumn_generators(row_index):
            self.clear_subcolumn(
                channel,
                row_index,
                pitch=pitch,
                volume=volume,
            )

    def adjust_transpose(
        self,
        channel: ChannelName,
        row_index: int,
        delta: int,
    ) -> None:
        """Shifts a channel cell's pitch by ``delta`` semitones, on the face the cell holds.

        An unset pitch counts as a step of zero, so the first nudge writes exactly ``delta`` as a
        step; a note moves to another note. The result is held within the range its face allows.
        """
        self.set_row(
            channel,
            row_index,
            pitch=shifted_pitch(self._current_pitch(channel, row_index), delta, channel),
        )

    def adjust_volume(
        self,
        channel: ChannelName,
        row_index: int,
        delta: int,
    ) -> None:
        """Shifts a channel cell's volume by ``delta``.

        An unset volume plays at full, so it counts as :data:`MAX_VOLUME` here:
        the first decrement steps down from the maximum.
        """
        self.set_row(
            channel,
            row_index,
            volume=self._current_volume(channel, row_index) + delta,
        )

    def row(
        self,
        channel: ChannelName,
        row_index: int,
    ) -> Optional[Row]:
        """The row stored at a cell, present while its channel holds a pattern reaching that far."""
        pattern_index = self._pattern_index_at_frame(channel)
        if pattern_index is None:
            return None

        pattern = self._controller.project.song.pattern(channel, pattern_index)
        if pattern is None or row_index >= pattern.length:
            return None

        return pattern.rows[row_index]

    def _current_pitch(
        self,
        channel: ChannelName,
        row_index: int,
    ) -> RowPitch:
        row = self.row(channel, row_index)
        if row is None or row.pitch is None:
            return Step(value=0)

        return row.pitch

    def _current_volume(self, channel: ChannelName, row_index: int) -> int:
        row = self.row(channel, row_index)
        if row is None or row.volume is None:
            return MAX_VOLUME

        return row.volume

    @property
    def frame_index(self) -> int:
        return self._frame_index

    def select_frame(self, frame_index: int) -> None:
        self._frame_index = frame_index
        self.push_tracker()

    def holds_voice(self, voice_id: str) -> bool:
        """Whether the project holds the voice a note names, which is what makes the note placeable."""
        return self._controller.project.voices.get(voice_id) is not None

    def used_generators(self, voice_id: str) -> List[ChannelName]:
        """The channels a sample provides instructions for, empty when it is unknown."""
        sample = self._controller.project.voices.get(voice_id)
        if sample is None:
            return []

        return self._used_generators(sample)

    def relevant_channels(self, row_index: int) -> List[ChannelName]:
        """The channels a sample-column transpose or volume edit reaches at ``row_index``.

        These are the channels the row's samples span where it names any, and otherwise the
        channels a sample from an earlier row of the frame is still playing on, matching where
        :meth:`set_sample_subcolumn` writes. A row where no sample plays reaches none.
        """
        return self._subcolumn_generators(row_index)

    def note_channels(self, row_index: int) -> List[ChannelName]:
        """The channels the sample column's voice slot reads at ``row_index``.

        The slot speaks for the samples a row names, and for every channel on a row naming
        none, so a row cut on every channel reads, and copies, as a cut. Mirrors
        :attr:`SequencerRowViewModel.note_channels`.
        """
        spanned = self.referenced_channels(row_index) or frozenset(ChannelName.items())
        return [channel for channel in ChannelName.items() if channel in spanned]

    def _pattern_index_at_frame(self, channel: ChannelName) -> Optional[int]:
        song = self._controller.project.song
        if self._frame_index < song.order_length():
            return song.order[self._frame_index].get(channel)

        return None

    def _create_frame_pattern(self, channel: ChannelName) -> Optional[int]:
        """Materializes a pattern for an empty slot at the current frame, on first edit.

        Providing content to a channel whose current frame is an empty (None) slot
        creates a fresh pattern and assigns it to that order position, so the
        arrangement grows as the user plays, capturing the input. Returns
        ``None`` when the frame is beyond the order length.
        """
        song = self._controller.project.song
        if self._frame_index >= song.order_length():
            return None

        pattern_index = self._controller.add_pattern(channel)
        self._controller.set_order_entry(
            channel,
            self._frame_index,
            pattern_index,
        )
        return pattern_index

    def _used_generators(self, voice: VoiceUnion) -> List[ChannelName]:
        """The channels a voice sounds on."""
        return list(voice_channels(voice))

    def _subcolumn_generators(self, row_index: int) -> List[ChannelName]:
        """Channels a sample-column transpose or volume edit writes to.

        A row naming a sample reaches that sample's span. A row naming none reaches the channels
        whose voice in force is a sample, read down the frame the way :meth:`carried_voice` reads
        it, so a channel cut since or now carrying an instrument takes nothing. Mirrors
        :attr:`SequencerRowViewModel.offset_channels`.
        """
        spanned = self.referenced_channels(row_index) or self._sample_carriers(
            {channel: self.carried_voice(channel, row_index) for channel in ChannelName.items()}
        )
        return [channel for channel in ChannelName.items() if channel in spanned]

    @staticmethod
    def _sample_carriers(
        carried: Mapping[ChannelName, Optional[VoiceUnion]],
    ) -> FrozenSet[ChannelName]:
        """The channels among ``carried`` whose voice in force is a sample."""
        return frozenset(
            channel
            for channel, voice in carried.items()
            if voice is not None and voice_kind(voice).places_across_channels
        )

    def referenced_channels(self, row_index: int) -> FrozenSet[ChannelName]:
        """The channels spanned by the samples a row names.

        Reads the row from every channel's pattern, so it reports a sample's whole
        span even where some of its cells stand empty. A row naming no sample
        references no channel, and :meth:`relevant_channels` then reads the samples
        still playing from earlier rows.
        """
        rows: Dict[ChannelName, Optional[Row]] = {}
        for channel in ChannelName.items():
            pattern_index = self._pattern_index_at_frame(channel)
            pattern = (
                self._controller.project.song.pattern(
                    channel,
                    pattern_index,
                )
                if pattern_index is not None
                else None
            )
            rows[channel] = pattern.rows[row_index] if pattern is not None else None

        return self._referenced_generators_from_rows(rows)

    def _referenced_generators_from_rows(
        self,
        rows: Dict[ChannelName, Optional[Row]],
    ) -> FrozenSet[ChannelName]:
        """The channels spanned by the samples a row names.

        A sample contributes the channels its reconstruction covers, so the sample column reasons
        about its whole span including channels whose cells stand empty. An instrument
        sounds on the one channel it is named in, so it contributes none and leaves the column
        speaking for samples alone. A row naming a voice the project no longer holds contributes
        the channel it sits on, which keeps that cell reachable while the reference stands.
        """
        relevant: Set[ChannelName] = set()
        resolved: Set[str] = set()
        for channel, row in rows.items():
            command = row.command if row is not None else None
            if not isinstance(command, NoteOn):
                continue

            voice_id = command.voice_id
            if voice_id in resolved:
                continue

            resolved.add(voice_id)
            voice = self._controller.project.voices.get(voice_id)
            if voice is None:
                relevant.add(channel)
            elif voice_kind(voice).places_across_channels:
                relevant.update(self._used_generators(voice))

        return frozenset(relevant)

    def _build_row(
        self,
        index: int,
        patterns: Dict[ChannelName, Pattern],
        carried: Dict[ChannelName, Optional[VoiceUnion]],
    ) -> SequencerRowViewModel:
        """One grid line, with each channel read in the terms of the voice it is carrying.

        ``carried`` walks down the frame with the rows, so a line bending a note it did not start
        still reads in that voice's terms, and the channels still playing a sample are the ones a
        pitch or a volume typed in the sample column reaches.
        """
        rows: Dict[ChannelName, Optional[Row]] = {}
        cells: Dict[ChannelName, SequencerCellViewModel] = {}
        for channel in ChannelName.items():
            pattern = patterns.get(channel)
            if pattern is not None and index < pattern.length:
                row = pattern.rows[index]
                rows[channel] = row
                carried[channel] = self._carried_voice(row, carried[channel])
                cells[channel] = self._build_cell(row)
            else:
                rows[channel] = None
                cells[channel] = _EMPTY_CELL

        return SequencerRowViewModel(
            index=index,
            cells=cells,
            sample_channels=self._referenced_generators_from_rows(rows),
            carried_channels=self._sample_carriers(carried),
        )

    def _carried_voice(
        self,
        row: Row,
        carried: Optional[VoiceUnion],
    ) -> Optional[VoiceUnion]:
        """The voice a channel carries once it has reached ``row``.

        A note column names the voice from that line on, a note-off leaves the channel carrying
        none, and a line naming neither plays on with whatever it already had.
        """
        match row.command:
            case NoteOn() as note_on:
                return self._controller.project.voices.get(note_on.voice_id)
            case NoteOff():
                return None
            case None:
                return carried

    def _build_cell(self, row: Row) -> SequencerCellViewModel:
        """One cell's three readings, the pitch printed in the face it was written in.

        A note reads as the note it names and a step as the step, whichever voice the row names,
        so the grid shows what the reader typed.
        """
        return SequencerCellViewModel(
            voice=display_command(
                self._controller.project.voices,
                row.command,
            ),
            transpose=display_pitch(row.pitch),
            volume=display_volume(row.volume),
            kind=self._named_kind(row.command),
            pitch=row.pitch,
            level=row.volume,
            command=row.command,
        )

    def _named_kind(self, command: Optional[NoteCommand]) -> Optional[VoiceKind]:
        """The kind of the voice a row names, absent where it names none the project holds.

        The cell states the voice it starts, so the kind is read from that command rather than from
        whatever the channel carries into the row: a line that only bends a note names nothing and
        takes the kind of nothing.
        """
        match command:
            case NoteOn() as note_on:
                voice = self._controller.project.voices.get(note_on.voice_id)
                return voice_kind(voice) if voice is not None else None
            case _:
                return None

    def _clamp_frame(self, frame_count: int) -> int:
        if frame_count == 0:
            return 0

        self._frame_index = max(0, min(self._frame_index, frame_count - 1))
        return self._frame_index
