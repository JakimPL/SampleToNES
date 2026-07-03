from typing import Dict, Final, List, Optional, Tuple

from sampletones_application.categories.elements.sequencer import SequencerHistoryElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.logic.sequencer.grid import SequencerGridLogic
from sampletones_application.logic.sequencer.samples import SequencerSamplesLogic
from sampletones_application.view_model.sequencer.history import (
    HistoryDetailRole,
    HistoryDetailSegment,
)
from sampletones_core.constants.enums import FeatureKey, GeneratorName, abbreviate_generator_names
from sampletones_core.utils.display import display_id, display_transpose, display_volume

Segments = Tuple[HistoryDetailSegment, ...]

_ARROW: Final[str] = ">"
_SUBCOLUMN_LETTERS: Final[Dict[str, str]] = {
    "instrument": "i",
    "transpose": "t",
    "volume": "v",
}
_SUBCOLUMN_ROLES: Final[Dict[str, HistoryDetailRole]] = {
    "instrument": HistoryDetailRole.INSTRUMENT,
    "transpose": HistoryDetailRole.TRANSPOSE,
    "volume": HistoryDetailRole.VOLUME,
}


class SequencerHistoryDetail:
    """Builds the coloured detail line for each undoable sequencer gesture.

    Every method mirrors the signature of the coordinator hook it describes, so it
    can be handed straight to ``_undoable`` as the ``detail`` callable. Each returns
    an ordered tuple of :class:`HistoryDetailSegment`, tagging each token with a
    semantic role that the panel later paints. Positions, rows and pattern indices
    read as two-digit hex; channels use the ``P``/``p``/``T``/``N`` abbreviations,
    concatenated when a sample-column gesture spans several channels.
    """

    def __init__(
        self,
        grid_logic: SequencerGridLogic,
        samples_logic: SequencerSamplesLogic,
        *,
        language_manager: LanguageManager,
    ) -> None:
        self._grid_logic = grid_logic
        self._samples_logic = samples_logic
        self._loop_on = language_manager[
            Page.SEQUENCER,
            Panel.HISTORY,
            TextType.LABEL,
            SequencerHistoryElements.LOOP_ON,
        ]
        self._loop_off = language_manager[
            Page.SEQUENCER,
            Panel.HISTORY,
            TextType.LABEL,
            SequencerHistoryElements.LOOP_OFF,
        ]

    def edit_row(
        self,
        row_index: int,
        generator: Optional[GeneratorName],
        sample_id: Optional[str],
        transpose: Optional[int],
        volume: Optional[int],
    ) -> Segments:
        affected = self._edit_row_generators(generator, sample_id, row_index)
        segments = list(self._location(row_index, generator, affected))
        if sample_id is not None:
            segments.append(self._arrow())
            segments.append(self._sample(sample_id))

        if transpose is not None:
            segments.append(self._segment("t", HistoryDetailRole.TRANSPOSE))
            segments.append(self._segment(display_transpose(transpose), HistoryDetailRole.TRANSPOSE))

        if volume is not None:
            segments.append(self._segment("v", HistoryDetailRole.VOLUME))
            segments.append(self._segment(display_volume(volume), HistoryDetailRole.VOLUME))

        return tuple(segments)

    def note_off(self, row_index: int, generator: Optional[GeneratorName]) -> Segments:
        return self._location(row_index, generator, GeneratorName.items())

    def clear_row(self, row_index: int, generator: Optional[GeneratorName]) -> Segments:
        return self._location(row_index, generator, GeneratorName.items())

    def clear_subcolumn(
        self,
        row_index: int,
        generator: Optional[GeneratorName],
        subcolumn: str,
    ) -> Segments:
        affected = (
            GeneratorName.items() if subcolumn == "instrument" else self._grid_logic.relevant_generators(row_index)
        )
        segments = list(self._location(row_index, generator, affected))
        segments.append(self._segment(_SUBCOLUMN_LETTERS[subcolumn], _SUBCOLUMN_ROLES[subcolumn]))
        return tuple(segments)

    def adjust_transpose(self, row_index: int, generator: Optional[GeneratorName], delta: int) -> Segments:
        affected = self._grid_logic.relevant_generators(row_index)
        segments = list(self._location(row_index, generator, affected))
        segments.append(self._segment(display_transpose(delta), HistoryDetailRole.TRANSPOSE))
        return tuple(segments)

    def adjust_volume(self, row_index: int, generator: Optional[GeneratorName], delta: int) -> Segments:
        affected = self._grid_logic.relevant_generators(row_index)
        segments = list(self._location(row_index, generator, affected))
        segments.append(self._segment(f"{delta:+d}", HistoryDetailRole.VOLUME))
        return tuple(segments)

    def add_frame(self, position: int) -> Segments:
        return (self._frame(position + 1),)

    def remove_frame(self, position: int) -> Segments:
        return (self._frame(position),)

    def clear_frame(self, position: int) -> Segments:
        return (self._frame(position),)

    def duplicate_frame(self, position: int) -> Segments:
        return (self._frame(position), self._arrow(), self._frame(position + 1))

    def move_frame(self, from_position: int, to_position: int) -> Segments:
        return (self._frame(from_position), self._arrow(), self._frame(to_position))

    def set_order_entry(
        self,
        generator: GeneratorName,
        position: int,
        pattern_index: Optional[int],
    ) -> Segments:
        return (
            self._frame(position),
            self._channel([generator]),
            self._arrow(),
            self._value(display_id(pattern_index)),
        )

    def set_master_entry(self, position: int, pattern_index: Optional[int]) -> Segments:
        return (
            self._frame(position),
            self._channel(GeneratorName.items()),
            self._arrow(),
            self._value(display_id(pattern_index)),
        )

    def add_sample(self, name: str) -> Segments:
        return (self._name(name),)

    def remove_sample(self, sample_id: str) -> Segments:
        return (self._sample(sample_id, colon=True), self._name(self._samples_logic.sample_name(sample_id)))

    def rename_sample(self, old_name: str, new_name: str) -> Segments:
        return (self._name(old_name), self._arrow(), self._name(new_name))

    def move_sample(self, sample_id: str, to_index: int) -> Segments:
        return (self._sample(sample_id), self._arrow(), self._value(display_id(to_index)))

    def duplicate_sample(self, sample_id: str) -> Segments:
        return (self._sample(sample_id, colon=True), self._name(self._samples_logic.sample_name(sample_id)))

    def set_sample_loop(self, sample_id: str, loop: bool) -> Segments:
        state = self._loop_on if loop else self._loop_off
        return (self._sample(sample_id, colon=True), self._value(state))

    def edit_reconstruction(
        self,
        sample_id: str,
        generator_name: GeneratorName,
        feature_key: FeatureKey,
    ) -> Segments:
        """Describes a regenerated sample: its position, channel, and edited feature."""
        return (
            self._sample(sample_id, colon=True),
            self._segment(generator_name.capitalized, HistoryDetailRole.CHANNEL),
            self._segment(feature_key.capitalized, HistoryDetailRole.FEATURE),
        )

    def value(self, number: int) -> Segments:
        return (self._value(str(number)),)

    def _edit_row_generators(
        self,
        generator: Optional[GeneratorName],
        sample_id: Optional[str],
        row_index: int,
    ) -> List[GeneratorName]:
        if generator is not None:
            return [generator]

        if sample_id is not None:
            return self._grid_logic.used_generators(sample_id)

        return self._grid_logic.relevant_generators(row_index)

    def _location(
        self,
        row_index: int,
        generator: Optional[GeneratorName],
        affected: List[GeneratorName],
    ) -> Segments:
        channels = [generator] if generator is not None else affected
        return (self._frame(self._grid_logic.frame_index), self._channel(channels), self._row(row_index))

    def _frame(self, index: int) -> HistoryDetailSegment:
        return HistoryDetailSegment(text=display_id(index), role=HistoryDetailRole.FRAME)

    def _row(self, index: int) -> HistoryDetailSegment:
        return HistoryDetailSegment(text=display_id(index), role=HistoryDetailRole.ROW)

    def _channel(self, generators: List[GeneratorName]) -> HistoryDetailSegment:
        return HistoryDetailSegment(text=abbreviate_generator_names(generators), role=HistoryDetailRole.CHANNEL)

    def _value(self, text: str) -> HistoryDetailSegment:
        return HistoryDetailSegment(text=text, role=HistoryDetailRole.VALUE)

    def _segment(self, text: str, role: HistoryDetailRole) -> HistoryDetailSegment:
        return HistoryDetailSegment(text=text, role=role)

    def _name(self, text: str) -> HistoryDetailSegment:
        return HistoryDetailSegment(text=text, role=HistoryDetailRole.NAME)

    def _sample(self, sample_id: str, *, colon: bool = False) -> HistoryDetailSegment:
        position = self._samples_logic.sample_position(sample_id)
        text = f"{position}:" if colon else position
        return HistoryDetailSegment(text=text, role=HistoryDetailRole.SAMPLE)

    def _arrow(self) -> HistoryDetailSegment:
        return HistoryDetailSegment(text=_ARROW, role=HistoryDetailRole.SEPARATOR)
