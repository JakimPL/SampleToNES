from typing import Callable, Dict, FrozenSet, List, Optional, Set

from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.view_model.sequencer.settings import (
    SequencerSettingsViewModel,
)
from sampletones_application.view_model.sequencer.tracker import (
    SequencerCellViewModel,
    SequencerRowViewModel,
    SequencerTrackerViewModel,
)
from sampletones_core.constants.enums import GeneratorName
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

        patterns: Dict[GeneratorName, Pattern] = {}
        if frame_count > 0:
            for generator in GeneratorName.items():
                index = song.order[frame_index].get(generator)
                pattern = song.pattern(generator, index) if index is not None else None
                if pattern is not None:
                    patterns[generator] = pattern

        row_count = self._frame_row_count(patterns, song.rows_per_pattern) if frame_count > 0 else 0
        rows = tuple(self._build_row(index, patterns) for index in range(row_count))
        return SequencerTrackerViewModel(
            frame_index=frame_index,
            frame_count=frame_count,
            rows=rows,
        )

    def _frame_row_count(
        self,
        patterns: Dict[GeneratorName, Pattern],
        rows_per_pattern: int,
    ) -> int:
        """Rows to show for the current frame.

        Empty (None) slots contribute no pattern, so a frame whose channels are all
        empty falls back to ``rows_per_pattern`` blank rows — keeping the frame
        editable so the first keystroke can auto-create a pattern for that channel.
        """
        lengths = [pattern.length for pattern in patterns.values()]
        if lengths:
            return max(lengths)

        return rows_per_pattern

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

    def set_row(
        self,
        generator: GeneratorName,
        row_index: int,
        *,
        command: Optional[NoteCommand] = None,
        transpose: Optional[int] = None,
        volume: Optional[int] = None,
    ) -> None:
        pattern_index = self._pattern_index_at_frame(generator)
        if pattern_index is None:
            pattern_index = self._create_frame_pattern(generator)

        if pattern_index is None:
            return

        self._controller.update_row(
            generator,
            pattern_index,
            row_index,
            command=command,
            transpose=transpose,
            volume=volume,
        )

    def clear_row(self, generator: GeneratorName, row_index: int) -> None:
        pattern_index = self._pattern_index_at_frame(generator)
        if pattern_index is None:
            return

        self._controller.clear_row(generator, pattern_index, row_index)

    def clear_subcolumn(
        self,
        generator: GeneratorName,
        row_index: int,
        *,
        instrument: bool = False,
        transpose: bool = False,
        volume: bool = False,
    ) -> None:
        pattern_index = self._pattern_index_at_frame(generator)
        if pattern_index is None:
            return

        self._controller.clear_row(
            generator,
            pattern_index,
            row_index,
            instrument=instrument,
            transpose=transpose,
            volume=volume,
        )

    def clear_all_generators(self, row_index: int) -> None:
        for generator in GeneratorName.items():
            self.clear_row(generator, row_index)

    def clear_subcolumn_all_generators(
        self,
        row_index: int,
        *,
        instrument: bool = False,
        transpose: bool = False,
        volume: bool = False,
    ) -> None:
        for generator in GeneratorName.items():
            self.clear_subcolumn(
                generator,
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
        generator the sample covers, and the remaining channels on that row are
        cleared so the row reflects exactly that sample. Clearing an empty sample
        id wipes the whole row.
        """
        if sample_id is None:
            self.clear_all_generators(row_index)
            return

        sample = self._controller.project.samples.get(sample_id)
        if sample is None:
            return

        used = self._used_generators(sample)
        for generator in GeneratorName.items():
            if generator in used:
                self.set_row(
                    generator,
                    row_index,
                    command=Instrument(
                        sample_id=sample_id,
                        generator_name=generator,
                    ),
                )
            else:
                self.clear_row(generator, row_index)

    def set_note_off(self, generator: GeneratorName, row_index: int) -> None:
        """Writes a note-off into one channel's cell, materialising the pattern if needed."""
        self.set_row(generator, row_index, command=NoteOff())

    def set_note_off_all_generators(self, row_index: int) -> None:
        """Cuts every channel at this row, the sample-column counterpart of :meth:`set_note_off`."""
        for generator in GeneratorName.items():
            self.set_note_off(generator, row_index)

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
        for generator in self._subcolumn_generators(row_index):
            self.set_row(
                generator,
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
        for generator in self._subcolumn_generators(row_index):
            self.clear_subcolumn(
                generator,
                row_index,
                transpose=transpose,
                volume=volume,
            )

    def adjust_transpose(
        self,
        generator: GeneratorName,
        row_index: int,
        delta: int,
    ) -> None:
        """Shifts a channel cell's transpose by ``delta`` semitones.

        An unset transpose counts as zero, so the first nudge writes exactly
        ``delta``; the controller clamps the result to the transpose range.
        """
        self.set_row(
            generator,
            row_index,
            transpose=self._current_transpose(generator, row_index) + delta,
        )

    def adjust_volume(
        self,
        generator: GeneratorName,
        row_index: int,
        delta: int,
    ) -> None:
        """Shifts a channel cell's volume by ``delta``.

        An unset volume plays at full, so it counts as :data:`MAX_VOLUME` here:
        the first decrement steps down from the maximum.
        """
        self.set_row(
            generator,
            row_index,
            volume=self._current_volume(generator, row_index) + delta,
        )

    def adjust_sample_transpose(self, row_index: int, delta: int) -> None:
        """Shifts transpose by ``delta`` across the sample column's channels."""
        for generator in self._subcolumn_generators(row_index):
            self.adjust_transpose(generator, row_index, delta)

    def adjust_sample_volume(self, row_index: int, delta: int) -> None:
        """Shifts volume by ``delta`` across the sample column's channels."""
        for generator in self._subcolumn_generators(row_index):
            self.adjust_volume(generator, row_index, delta)

    def _current_row(
        self,
        generator: GeneratorName,
        row_index: int,
    ) -> Optional[Row]:
        pattern_index = self._pattern_index_at_frame(generator)
        if pattern_index is None:
            return None

        pattern = self._controller.project.song.pattern(generator, pattern_index)
        if pattern is None or row_index >= pattern.length:
            return None

        return pattern.rows[row_index]

    def _current_transpose(
        self,
        generator: GeneratorName,
        row_index: int,
    ) -> int:
        row = self._current_row(generator, row_index)
        if row is None or row.transpose is None:
            return 0

        return row.transpose

    def _current_volume(self, generator: GeneratorName, row_index: int) -> int:
        row = self._current_row(generator, row_index)
        if row is None or row.volume is None:
            return MAX_VOLUME

        return row.volume

    @property
    def frame_index(self) -> int:
        return self._frame_index

    def select_frame(self, frame_index: int) -> None:
        self._frame_index = frame_index
        self.push_tracker()

    def used_generators(self, sample_id: str) -> List[GeneratorName]:
        """The channels a sample provides instructions for, empty when it is unknown."""
        sample = self._controller.project.samples.get(sample_id)
        if sample is None:
            return []

        return self._used_generators(sample)

    def relevant_generators(self, row_index: int) -> List[GeneratorName]:
        """The channels a sample-column subcolumn edit reaches at ``row_index``.

        Follows the row's sample channels when one governs it, and otherwise every
        channel, matching where :meth:`set_sample_subcolumn` writes.
        """
        return self._subcolumn_generators(row_index)

    def _pattern_index_at_frame(self, generator: GeneratorName) -> Optional[int]:
        song = self._controller.project.song
        if self._frame_index < song.order_length():
            return song.order[self._frame_index].get(generator)

        return None

    def _create_frame_pattern(self, generator: GeneratorName) -> Optional[int]:
        """Materialises a pattern for an empty slot at the current frame, on first edit.

        Providing content to a channel whose current frame is an empty (None) slot
        creates a fresh pattern and assigns it to that order position, so the
        arrangement grows as the user plays, capturing the input. Returns
        ``None`` when the frame is beyond the order length.
        """
        song = self._controller.project.song
        if self._frame_index >= song.order_length():
            return None

        pattern_index = self._controller.add_pattern(generator)
        self._controller.set_order_entry(
            generator,
            self._frame_index,
            pattern_index,
        )
        return pattern_index

    def _used_generators(self, sample: Sample) -> List[GeneratorName]:
        """The channels a sample's reconstruction provides instructions for."""
        return [
            generator
            for generator in GeneratorName.items()
            if sample.reconstruction.get_generator_instructions(generator)
        ]

    def _subcolumn_generators(self, row_index: int) -> List[GeneratorName]:
        """Channels a sample-column transpose/volume edit writes to.

        Falls back to every channel when no sample constrains the row, mirroring
        :attr:`SequencerRowViewModel.subcolumn_generators`.
        """
        relevant = self._relevant_generators(row_index)
        if not relevant:
            return GeneratorName.items()

        return [generator for generator in GeneratorName.items() if generator in relevant]

    def _relevant_generators(self, row_index: int) -> FrozenSet[GeneratorName]:
        rows: Dict[GeneratorName, Optional[Row]] = {}
        for generator in GeneratorName.items():
            pattern_index = self._pattern_index_at_frame(generator)
            pattern = (
                self._controller.project.song.pattern(
                    generator,
                    pattern_index,
                )
                if pattern_index is not None
                else None
            )
            rows[generator] = pattern.rows[row_index] if pattern is not None else None

        return self._relevant_generators_from_rows(rows)

    def _relevant_generators_from_rows(
        self,
        rows: Dict[GeneratorName, Optional[Row]],
    ) -> FrozenSet[GeneratorName]:
        """The channels spanned by the samples referenced on a row.

        Each referenced sample contributes the channels its reconstruction covers,
        so the sample column reasons about a sample's whole channel span, including
        channels whose cells are empty.
        """
        relevant: Set[GeneratorName] = set()
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
                relevant.add(command.generator_name)
            else:
                relevant.update(self._used_generators(sample))

        return frozenset(relevant)

    def _build_row(
        self,
        index: int,
        patterns: Dict[GeneratorName, Pattern],
    ) -> SequencerRowViewModel:
        rows: Dict[GeneratorName, Optional[Row]] = {}
        cells: Dict[GeneratorName, SequencerCellViewModel] = {}
        for generator in GeneratorName.items():
            pattern = patterns.get(generator)
            if pattern is not None and index < pattern.length:
                row = pattern.rows[index]
                rows[generator] = row
                cells[generator] = self._build_cell(row)
            else:
                rows[generator] = None
                cells[generator] = _EMPTY_CELL

        return SequencerRowViewModel(
            index=index,
            cells=cells,
            relevant_generators=self._relevant_generators_from_rows(rows),
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
