from typing import Dict, Final, List, Optional

from sampletones_application.logic.sequencer.samples import SequencerSamplesLogic
from sampletones_application.logic.sequencer.tracker import SequencerTrackerLogic
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_application.view_model.shared.history import (
    HistoryDetail,
    HistoryDetailRole,
    HistoryDetailSegment,
    HistoryDetailWord,
    HistoryDetailWordSegment,
)
from sampletones_core.constants.enums import (
    FeatureKey,
    GeneratorName,
    abbreviate_generator_names,
)
from sampletones_core.utils.display import display_id, display_transpose, display_volume

Segments = HistoryDetail

_ARROW: Final[str] = ">"
_SUBCOLUMN_LETTERS: Final[Dict[SubColumn, str]] = {
    SubColumn.INSTRUMENT: "i",
    SubColumn.TRANSPOSE: "t",
    SubColumn.VOLUME: "v",
}
_SUBCOLUMN_ROLES: Final[Dict[SubColumn, HistoryDetailRole]] = {
    SubColumn.INSTRUMENT: HistoryDetailRole.INSTRUMENT,
    SubColumn.TRANSPOSE: HistoryDetailRole.TRANSPOSE,
    SubColumn.VOLUME: HistoryDetailRole.VOLUME,
}
_FEATURE_LETTERS: Final[Dict[FeatureKey, str]] = {
    FeatureKey.INITIAL_PITCH: "i",
    FeatureKey.VOLUME: "v",
    FeatureKey.ARPEGGIO: "a",
    FeatureKey.PITCH: "p",
    FeatureKey.HI_PITCH: "h",
    FeatureKey.DUTY_CYCLE: "d",
}
_FEATURE_ROLES: Final[Dict[FeatureKey, HistoryDetailRole]] = {
    FeatureKey.INITIAL_PITCH: HistoryDetailRole.FEATURE_PITCH,
    FeatureKey.VOLUME: HistoryDetailRole.FEATURE_VOLUME,
    FeatureKey.ARPEGGIO: HistoryDetailRole.FEATURE_ARPEGGIO,
    FeatureKey.PITCH: HistoryDetailRole.FEATURE_PITCH,
    FeatureKey.HI_PITCH: HistoryDetailRole.FEATURE_PITCH,
    FeatureKey.DUTY_CYCLE: HistoryDetailRole.FEATURE_DUTY_CYCLE,
}


class SequencerHistoryDetail:
    """Builds the coloured detail line for each undoable sequencer gesture.

    Every method mirrors the signature of the coordinator hook it describes, so it
    can be handed straight to ``_undoable`` as the ``detail`` callable. Each returns
    an ordered tuple of :class:`HistoryDetailSegment`, tagging each token with a
    semantic role that the panel later paints. Positions, rows and pattern indices
    read as two-digit hex; channels use the ``P``/``p``/``T``/``N`` abbreviations,
    concatenated when a sample-column gesture spans several channels.
    Language-managed words — the loop on/off states — are emitted as
    :class:`HistoryDetailWordSegment` keys and translated when the history view is
    built, keeping committed entries language-independent.
    """

    def __init__(
        self,
        tracker_logic: SequencerTrackerLogic,
        samples_logic: SequencerSamplesLogic,
    ) -> None:
        self._tracker_logic = tracker_logic
        self._samples_logic = samples_logic

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
            segments.append(self._subcolumn(SubColumn.TRANSPOSE))
            segments.append(
                self._segment(
                    display_transpose(transpose),
                    HistoryDetailRole.TRANSPOSE,
                ),
            )

        if volume is not None:
            segments.append(self._subcolumn(SubColumn.VOLUME))
            segments.append(
                self._segment(display_volume(volume), HistoryDetailRole.VOLUME),
            )

        return tuple(segments)

    def note_off(
        self,
        row_index: int,
        generator: Optional[GeneratorName],
    ) -> Segments:
        return self._location(row_index, generator, GeneratorName.items())

    def clear_row(
        self,
        row_index: int,
        generator: Optional[GeneratorName],
    ) -> Segments:
        return self._location(row_index, generator, GeneratorName.items())

    def clear_subcolumn(
        self,
        row_index: int,
        generator: Optional[GeneratorName],
        subcolumn: SubColumn,
    ) -> Segments:
        affected = (
            GeneratorName.items()
            if subcolumn is SubColumn.INSTRUMENT
            else self._tracker_logic.relevant_generators(row_index)
        )
        segments = list(self._location(row_index, generator, affected))
        segments.append(self._subcolumn(subcolumn))
        return tuple(segments)

    def adjust_transpose(
        self,
        row_index: int,
        generator: Optional[GeneratorName],
        delta: int,
    ) -> Segments:
        affected = self._tracker_logic.relevant_generators(row_index)
        segments = list(self._location(row_index, generator, affected))
        segments.append(
            self._segment(display_transpose(delta), HistoryDetailRole.TRANSPOSE),
        )
        return tuple(segments)

    def adjust_volume(
        self,
        row_index: int,
        generator: Optional[GeneratorName],
        delta: int,
    ) -> Segments:
        affected = self._tracker_logic.relevant_generators(row_index)
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
        return (
            self._frame(from_position),
            self._arrow(),
            self._frame(to_position),
        )

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

    def set_master_entry(
        self,
        position: int,
        pattern_index: Optional[int],
    ) -> Segments:
        return (
            self._frame(position),
            self._channel(GeneratorName.items()),
            self._arrow(),
            self._value(display_id(pattern_index)),
        )

    def add_sample(self, name: str) -> Segments:
        return (self._name(name),)

    def remove_sample(self, sample_id: str) -> Segments:
        return (
            self._sample(sample_id, colon=True),
            self._name(self._samples_logic.sample_name(sample_id)),
        )

    def replace_sample(self, sample_id: str, name: str) -> Segments:
        """Describes a reconstruction substitution as the sample's position and the two names.

        ``name`` is the incoming reconstruction's, read against the sample's current one, so the
        caller builds this detail while the sample still holds the reconstruction being replaced.
        """
        return (
            self._sample(sample_id, colon=True),
            self._name(self._samples_logic.sample_name(sample_id)),
            self._arrow(),
            self._name(name),
        )

    def rename_sample(self, old_name: str, new_name: str) -> Segments:
        return (self._name(old_name), self._arrow(), self._name(new_name))

    def move_sample(self, sample_id: str, to_index: int) -> Segments:
        return (
            self._sample(sample_id),
            self._arrow(),
            self._value(display_id(to_index)),
        )

    def duplicate_sample(self, sample_id: str) -> Segments:
        return (
            self._sample(sample_id, colon=True),
            self._name(self._samples_logic.sample_name(sample_id)),
        )

    def set_sample_loop(self, sample_id: str, loop: bool) -> Segments:
        word = HistoryDetailWord.LOOP_ON if loop else HistoryDetailWord.LOOP_OFF
        return (
            self._sample(sample_id, colon=True),
            HistoryDetailWordSegment(word=word, role=HistoryDetailRole.VALUE),
        )

    def edit_reconstruction(
        self,
        sample_id: str,
        generator_name: GeneratorName,
        feature_key: FeatureKey,
    ) -> Segments:
        """Describes a regenerated sample: its position, channel, and edited feature.

        The channel and the feature both render abbreviated — the ``P``/``p``/``T``/``N``
        channel letter and the feature's one-letter code in the same colour the details
        tab plots it with — mirroring the tracker rows.
        """
        return (
            self._sample(sample_id, colon=True),
            self._channel([generator_name]),
            self._segment(_FEATURE_LETTERS[feature_key], _FEATURE_ROLES[feature_key]),
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
            return self._tracker_logic.used_generators(sample_id)

        return self._tracker_logic.relevant_generators(row_index)

    def _location(
        self,
        row_index: int,
        generator: Optional[GeneratorName],
        affected: List[GeneratorName],
    ) -> Segments:
        channels = [generator] if generator is not None else affected
        return (
            self._frame(self._tracker_logic.frame_index),
            self._channel(channels),
            self._row(row_index),
        )

    def _frame(self, index: int) -> HistoryDetailSegment:
        return HistoryDetailSegment(
            text=display_id(index),
            role=HistoryDetailRole.FRAME,
        )

    def _row(self, index: int) -> HistoryDetailSegment:
        return HistoryDetailSegment(
            text=display_id(index),
            role=HistoryDetailRole.ROW,
        )

    def _channel(self, generators: List[GeneratorName]) -> HistoryDetailSegment:
        return HistoryDetailSegment(
            text=abbreviate_generator_names(generators),
            role=HistoryDetailRole.CHANNEL,
        )

    def _value(self, text: str) -> HistoryDetailSegment:
        return HistoryDetailSegment(text=text, role=HistoryDetailRole.VALUE)

    def _segment(
        self,
        text: str,
        role: HistoryDetailRole,
    ) -> HistoryDetailSegment:
        return HistoryDetailSegment(text=text, role=role)

    def _subcolumn(self, subcolumn: SubColumn) -> HistoryDetailSegment:
        return self._segment(
            _SUBCOLUMN_LETTERS[subcolumn],
            _SUBCOLUMN_ROLES[subcolumn],
        )

    def _name(self, text: str) -> HistoryDetailSegment:
        return HistoryDetailSegment(
            text=text,
            role=HistoryDetailRole.NAME,
        )

    def _sample(
        self,
        sample_id: str,
        *,
        colon: bool = False,
    ) -> HistoryDetailSegment:
        position = self._samples_logic.sample_position(sample_id)
        text = f"{position}:" if colon else position
        return HistoryDetailSegment(text=text, role=HistoryDetailRole.SAMPLE)

    def _arrow(self) -> HistoryDetailSegment:
        return HistoryDetailSegment(
            text=_ARROW,
            role=HistoryDetailRole.SEPARATOR,
        )
