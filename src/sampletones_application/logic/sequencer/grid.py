from typing import Callable, Dict, Optional

from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.view_model.sequencer.grid import (
    SequencerCellViewModel,
    SequencerGridViewModel,
    SequencerRowViewModel,
)
from sampletones_application.view_model.sequencer.settings import SequencerSettingsViewModel
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.project.instruments.instrument import Instrument
from sampletones_core.project.patterns.pattern import Pattern
from sampletones_core.project.patterns.row import Row
from sampletones_core.utils.display import (
    display_id,
    display_instrument,
    display_transpose,
    display_volume,
)
from sampletones_shared.utils.callbacks import CallbackMixin

_EMPTY_CELL = SequencerCellViewModel(
    instrument=display_id(None),
    transpose=display_transpose(None),
    volume=display_volume(None),
)


class SequencerGridLogic(CallbackMixin):
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
        self.on_grid_changed: Optional[Callable[[SequencerGridViewModel], None]] = None
        self.on_frame_changed: Optional[Callable[[int], None]] = None

    @property
    def settings(self) -> SequencerSettingsViewModel:
        settings = self._controller.project.settings
        return SequencerSettingsViewModel(
            change_rate=settings.change_rate,
            tempo=settings.tempo,
            speed=settings.speed,
            rows_per_pattern=settings.rows_per_pattern,
        )

    def build_grid(self) -> SequencerGridViewModel:
        song = self._controller.project.song
        frame_count = max((len(song[generator].order) for generator in GeneratorName.items()), default=0)
        frame_index = self._clamp_frame(frame_count)

        patterns: Dict[GeneratorName, Pattern] = {}
        row_count = 0
        for generator in GeneratorName.items():
            channel = song[generator]
            if frame_index < len(channel.order):
                pattern = channel.pattern(channel.order[frame_index])
                patterns[generator] = pattern
                row_count = max(row_count, pattern.length)

        rows = tuple(self._build_row(index, patterns) for index in range(row_count))
        return SequencerGridViewModel(frame_index=frame_index, frame_count=frame_count, rows=rows)

    def push_settings(self) -> None:
        self.call(self.on_settings_changed, self.settings)

    def push_grid(self) -> None:
        view_model = self.build_grid()
        self.call(self.on_grid_changed, view_model)
        self.call(self.on_frame_changed, view_model.frame_index)

    def refresh(self) -> None:
        self.push_settings()
        self.push_grid()

    def set_change_rate(self, change_rate: int) -> None:
        self._controller.set_change_rate(change_rate)

    def set_tempo(self, tempo: int) -> None:
        self._controller.set_tempo(tempo)

    def set_speed(self, speed: int) -> None:
        self._controller.set_speed(speed)

    def set_row(
        self,
        generator: GeneratorName,
        row_index: int,
        *,
        instrument: Optional[Instrument] = None,
        transpose: Optional[int] = None,
        volume: Optional[int] = None,
    ) -> None:
        pattern_id = self._pattern_id_at_frame(generator)
        if pattern_id is None:
            return

        self._controller.set_row(
            generator,
            pattern_id,
            row_index,
            instrument=instrument,
            transpose=transpose,
            volume=volume,
        )

    def clear_row(self, generator: GeneratorName, row_index: int) -> None:
        pattern_id = self._pattern_id_at_frame(generator)
        if pattern_id is None:
            return

        self._controller.clear_row(generator, pattern_id, row_index)

    def clear_all_generators(self, row_index: int) -> None:
        for generator in GeneratorName.items():
            self.clear_row(generator, row_index)

    def set_row_all_generators(self, row_index: int, sample_id: Optional[str]) -> None:
        for generator in GeneratorName.items():
            instrument = Instrument(sample_id=sample_id, generator_name=generator) if sample_id is not None else None
            self.set_row(generator, row_index, instrument=instrument)

    def select_frame(self, frame_index: int) -> None:
        self._frame_index = frame_index
        self.push_grid()

    def _pattern_id_at_frame(self, generator: GeneratorName) -> Optional[str]:
        channel = self._controller.project.song[generator]
        if self._frame_index < len(channel.order):
            return channel.order[self._frame_index]

        return None

    def _build_row(self, index: int, patterns: Dict[GeneratorName, Pattern]) -> SequencerRowViewModel:
        cells: Dict[GeneratorName, SequencerCellViewModel] = {}
        for generator in GeneratorName.items():
            pattern = patterns.get(generator)
            if pattern is not None and index < pattern.length:
                cells[generator] = self._build_cell(pattern.rows[index])
            else:
                cells[generator] = _EMPTY_CELL

        return SequencerRowViewModel(index=index, cells=cells)

    def _build_cell(self, row: Row) -> SequencerCellViewModel:
        return SequencerCellViewModel(
            instrument=display_instrument(self._controller.project.samples, row.instrument),
            transpose=display_transpose(row.transpose),
            volume=display_volume(row.volume),
        )

    def _clamp_frame(self, frame_count: int) -> int:
        if frame_count == 0:
            return 0

        self._frame_index = max(0, min(self._frame_index, frame_count - 1))
        return self._frame_index
