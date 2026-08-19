from typing import Callable, Dict, FrozenSet, List, Optional, Set

from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.view_model.sequencer.settings import (
    SequencerSettingsViewModel,
)
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_application.view_model.sequencer.tracker import (
    SequencerCellViewModel,
    SequencerRowViewModel,
    SequencerTrackerViewModel,
)
from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import MAX_VOLUME
from sampletones_core.project.instruments.instrument import Instrument
from sampletones_core.project.instruments.note_off import NoteOff
from sampletones_core.project.instruments.sample import Sample
from sampletones_core.project.patterns.pattern import Pattern
from sampletones_core.project.patterns.row import NoteCommand, Row
from sampletones_core.utils.display import (
    display_command,
    display_id,
    display_transpose,
    display_volume,
)
from sampletones_shared.utils.callbacks import CallbackMixin

_EMPTY_CELL = SequencerCellViewModel(
    instrument=display_id(None),
    transpose=display_transpose(None),
    volume=display_volume(None),
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
        rows = tuple(self._build_row(index, patterns) for index in range(self.frame_row_count()))
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

        From the sample column an instrument reaches every channel, since the sample
        it names is the row's whole note, while transpose and volume follow the
        channels that column governs.
        """
        instrument = subcolumn is SubColumn.INSTRUMENT
        transpose = subcolumn is SubColumn.TRANSPOSE
        volume = subcolumn is SubColumn.VOLUME
        if channel is not None:
            self.clear_subcolumn(
                channel,
                row_index,
                instrument=instrument,
                transpose=transpose,
                volume=volume,
            )
        elif instrument:
            self.clear_subcolumn_all_generators(row_index, instrument=True)
        else:
            self.clear_sample_subcolumn(
                row_index,
                transpose=transpose,
                volume=volume,
            )

    def write_cell(
        self,
        row_index: int,
        channel: Optional[ChannelName],
        sample_id: Optional[str],
        transpose: Optional[int],
        volume: Optional[int],
    ) -> None:
        """Writes the value a cell edit carries, keeping the rest of the cell as it stands.

        An edit names one subcolumn, so a sample takes the write whenever one
        arrives, and an offset lands on its own otherwise.
        """
        if sample_id is not None:
            self.place_note(row_index, channel, sample_id)
        elif transpose is not None or volume is not None:
            self.set_cell_subcolumn(
                row_index,
                channel,
                transpose=transpose,
                volume=volume,
            )

    def place_note(
        self,
        row_index: int,
        channel: Optional[ChannelName],
        sample_id: str,
    ) -> None:
        if channel is None:
            self.set_sample_instrument(row_index, sample_id)
        else:
            self.set_row(
                channel,
                row_index,
                command=Instrument(
                    sample_id=sample_id,
                    channel_name=channel,
                ),
            )

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
        transpose: Optional[int] = None,
        volume: Optional[int] = None,
    ) -> None:
        if channel is None:
            self.set_sample_subcolumn(
                row_index,
                transpose=transpose,
                volume=volume,
            )
        else:
            self.set_row(
                channel,
                row_index,
                transpose=transpose,
                volume=volume,
            )

    def set_row(
        self,
        channel: ChannelName,
        row_index: int,
        *,
        command: Optional[NoteCommand] = None,
        transpose: Optional[int] = None,
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
            transpose=transpose,
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
        instrument: bool = False,
        transpose: bool = False,
        volume: bool = False,
    ) -> None:
        pattern_index = self._pattern_index_at_frame(channel)
        if pattern_index is None:
            return

        self._controller.clear_row(
            channel,
            pattern_index,
            row_index,
            instrument=instrument,
            transpose=transpose,
            volume=volume,
        )

    def clear_all_channels(self, row_index: int) -> None:
        for channel in ChannelName.items():
            self.clear_row(channel, row_index)

    def clear_subcolumn_all_generators(
        self,
        row_index: int,
        *,
        instrument: bool = False,
        transpose: bool = False,
        volume: bool = False,
    ) -> None:
        for channel in ChannelName.items():
            self.clear_subcolumn(
                channel,
                row_index,
                instrument=instrument,
                transpose=transpose,
                volume=volume,
            )

    def set_sample_instrument(
        self,
        row_index: int,
        sample_id: Optional[str],
    ) -> None:
        """Places a sample across the channels its reconstruction uses.

        The sample column is authoritative: the instrument is written to every
        channel the sample covers, and the remaining channels on that row are
        cleared so the row reflects exactly that sample. Clearing an empty sample
        id wipes the whole row.
        """
        if sample_id is None:
            self.clear_all_channels(row_index)
            return

        sample = self._controller.project.samples.get(sample_id)
        if sample is None:
            return

        used = self._used_generators(sample)
        for channel in ChannelName.items():
            if channel in used:
                self.set_row(
                    channel,
                    row_index,
                    command=Instrument(
                        sample_id=sample_id,
                        channel_name=channel,
                    ),
                )
            else:
                self.clear_row(channel, row_index)

    def set_note_off(self, channel: ChannelName, row_index: int) -> None:
        """Writes a note-off into one channel's cell, materialising the pattern if needed."""
        self.set_row(channel, row_index, command=NoteOff())

    def set_note_off_all_generators(self, row_index: int) -> None:
        """Cuts every channel at this row, the sample-column counterpart of :meth:`set_note_off`."""
        for channel in ChannelName.items():
            self.set_note_off(channel, row_index)

    def set_sample_subcolumn(
        self,
        row_index: int,
        *,
        transpose: Optional[int] = None,
        volume: Optional[int] = None,
    ) -> None:
        """Synchronises a subcolumn across the row's relevant channels.

        Transpose and volume exist independently of an instrument: they follow the
        sample's channels when one is present, and otherwise reach every channel, so
        a value typed in the sample column always lands somewhere.
        """
        for channel in self._subcolumn_generators(row_index):
            self.set_row(
                channel,
                row_index,
                transpose=transpose,
                volume=volume,
            )

    def clear_sample_subcolumn(
        self,
        row_index: int,
        *,
        transpose: bool = False,
        volume: bool = False,
    ) -> None:
        for channel in self._subcolumn_generators(row_index):
            self.clear_subcolumn(
                channel,
                row_index,
                transpose=transpose,
                volume=volume,
            )

    def adjust_transpose(
        self,
        channel: ChannelName,
        row_index: int,
        delta: int,
    ) -> None:
        """Shifts a channel cell's transpose by ``delta`` semitones.

        An unset transpose counts as zero, so the first nudge writes exactly
        ``delta``; the controller clamps the result to the transpose range.
        """
        self.set_row(
            channel,
            row_index,
            transpose=self._current_transpose(channel, row_index) + delta,
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

    def _current_transpose(
        self,
        channel: ChannelName,
        row_index: int,
    ) -> int:
        row = self.row(channel, row_index)
        if row is None or row.transpose is None:
            return 0

        return row.transpose

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

    def holds_sample(self, sample_id: str) -> bool:
        """Whether the project holds the sample a note names, which is what makes the note placeable."""
        return self._controller.project.samples.get(sample_id) is not None

    def used_generators(self, sample_id: str) -> List[ChannelName]:
        """The channels a sample provides instructions for, empty when it is unknown."""
        sample = self._controller.project.samples.get(sample_id)
        if sample is None:
            return []

        return self._used_generators(sample)

    def relevant_channels(self, row_index: int) -> List[ChannelName]:
        """The channels a sample-column subcolumn edit reaches at ``row_index``.

        Follows the row's sample channels when one governs it, and otherwise every
        channel, matching where :meth:`set_sample_subcolumn` writes.
        """
        return self._subcolumn_generators(row_index)

    def _pattern_index_at_frame(self, channel: ChannelName) -> Optional[int]:
        song = self._controller.project.song
        if self._frame_index < song.order_length():
            return song.order[self._frame_index].get(channel)

        return None

    def _create_frame_pattern(self, channel: ChannelName) -> Optional[int]:
        """Materialises a pattern for an empty slot at the current frame, on first edit.

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

    def _used_generators(self, sample: Sample) -> List[ChannelName]:
        """The channels a sample's reconstruction provides instructions for."""
        return [channel for channel in ChannelName.items() if sample.reconstruction.get_channel_instructions(channel)]

    def _subcolumn_generators(self, row_index: int) -> List[ChannelName]:
        """Channels a sample-column transpose/volume edit writes to.

        Falls back to every channel when no sample constrains the row, mirroring
        :attr:`SequencerRowViewModel.subcolumn_channels`.
        """
        referenced = self.referenced_channels(row_index)
        if not referenced:
            return ChannelName.items()

        return [channel for channel in ChannelName.items() if channel in referenced]

    def referenced_channels(self, row_index: int) -> FrozenSet[ChannelName]:
        """The channels spanned by the samples a row names.

        Reads the row from every channel's pattern, so it reports a sample's whole
        span even where some of its cells stand empty. A row naming no sample
        references no channel, which is what :meth:`relevant_channels` widens to
        every channel.
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
        """The channels spanned by the samples referenced on a row.

        Each referenced sample contributes the channels its reconstruction covers,
        so the sample column reasons about a sample's whole channel span, including
        channels whose cells are empty.
        """
        relevant: Set[ChannelName] = set()
        resolved: Set[str] = set()
        for row in rows.values():
            command = row.command if row is not None else None
            if not isinstance(command, Instrument):
                continue

            sample_id = command.sample_id
            if sample_id in resolved:
                continue

            resolved.add(sample_id)
            sample = self._controller.project.samples.get(sample_id)
            if sample is None:
                relevant.add(command.channel_name)
            else:
                relevant.update(self._used_generators(sample))

        return frozenset(relevant)

    def _build_row(
        self,
        index: int,
        patterns: Dict[ChannelName, Pattern],
    ) -> SequencerRowViewModel:
        rows: Dict[ChannelName, Optional[Row]] = {}
        cells: Dict[ChannelName, SequencerCellViewModel] = {}
        for channel in ChannelName.items():
            pattern = patterns.get(channel)
            if pattern is not None and index < pattern.length:
                row = pattern.rows[index]
                rows[channel] = row
                cells[channel] = self._build_cell(row)
            else:
                rows[channel] = None
                cells[channel] = _EMPTY_CELL

        return SequencerRowViewModel(
            index=index,
            cells=cells,
            relevant_channels=self._referenced_generators_from_rows(rows),
        )

    def _build_cell(self, row: Row) -> SequencerCellViewModel:
        return SequencerCellViewModel(
            instrument=display_command(
                self._controller.project.samples,
                row.command,
            ),
            transpose=display_transpose(row.transpose),
            volume=display_volume(row.volume),
        )

    def _clamp_frame(self, frame_count: int) -> int:
        if frame_count == 0:
            return 0

        self._frame_index = max(0, min(self._frame_index, frame_count - 1))
        return self._frame_index
