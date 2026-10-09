from typing import Final, List

from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.constants.general import MAX_VOLUME, SILENT_VOLUME
from sampletones_core.exporters.truncation import EnvelopeTruncation
from sampletones_core.formats.bitphase.envelopes import features_to_envelopes
from sampletones_core.formats.bitphase.preset import instrument_to_preset
from sampletones_core.formats.bitphase.specification.macros import MAX_MACRO_LENGTH, NesMacroField
from sampletones_core.formats.bitphase.truncation import document_truncation, preset_truncation
from sampletones_core.formats.bitphase.tuning import DEFAULT_TUNING_TABLE

from .conftest import build_features, build_instrument

SHORT_ENVELOPE: Final[int] = 16
LONG_ENVELOPE: Final[int] = 600


def held(length: int) -> List[int]:
    """A volume of ``length`` items that goes on sounding."""
    return [MAX_VOLUME] * length


def released(length: int) -> List[int]:
    """A volume of ``length`` items whose last one releases the note."""
    return held(length - 1) + [SILENT_VOLUME]


class TestWhatADocumentReportsLeavingOut:
    def test_a_slice_within_a_macro_reports_nothing(self) -> None:
        assert document_truncation(build_features(held(MAX_MACRO_LENGTH))) is None

    def test_a_slice_past_a_macro_reports_both_counts(self) -> None:
        assert document_truncation(build_features(held(LONG_ENVELOPE))) == EnvelopeTruncation(
            frames=MAX_MACRO_LENGTH,
            source_frames=LONG_ENVELOPE,
            instruments=1,
        )

    def test_a_document_keeps_the_contour_whole(self) -> None:
        """The contour rides a table, which holds any length."""
        features = build_features(held(SHORT_ENVELOPE), arpeggio=[0] * LONG_ENVELOPE)
        assert document_truncation(features) is None

    def test_a_volume_keeps_its_release_within_the_count_reported(self) -> None:
        """The note has to end, so the release is among the values the report counts."""
        features = build_features(released(LONG_ENVELOPE))
        truncation = document_truncation(features)
        macro = features_to_envelopes(
            features,
            ChannelName.PULSE1,
            tuning_table=DEFAULT_TUNING_TABLE,
        ).macros[NesMacroField.VOLUME_OR_RATE]

        assert truncation is not None
        assert len(macro.values) == truncation.frames
        assert macro.values[-1] == SILENT_VOLUME


class TestWhatAPresetReportsLeavingOut:
    def test_a_slice_within_a_macro_reports_nothing(self) -> None:
        assert preset_truncation(build_features(held(MAX_MACRO_LENGTH))) is None

    def test_a_slice_past_a_macro_reports_both_counts(self) -> None:
        assert preset_truncation(build_features(held(LONG_ENVELOPE))) == EnvelopeTruncation(
            frames=MAX_MACRO_LENGTH,
            source_frames=LONG_ENVELOPE,
            instruments=1,
        )

    def test_a_preset_shortens_the_contour(self) -> None:
        """A preset folds the contour into the tone offset, which a macro carries."""
        features = build_features(held(SHORT_ENVELOPE), arpeggio=[0] * LONG_ENVELOPE)
        offsets = instrument_to_preset(build_instrument("Sweep", features)).macros[NesMacroField.TONE_ADD]

        assert preset_truncation(features) == EnvelopeTruncation(
            frames=len(offsets.values),
            source_frames=LONG_ENVELOPE,
            instruments=1,
        )

    def test_a_bend_past_a_macro_is_reported(self) -> None:
        features = build_features(held(SHORT_ENVELOPE), bend=[1] * LONG_ENVELOPE)
        assert preset_truncation(features) == EnvelopeTruncation(
            frames=MAX_MACRO_LENGTH,
            source_frames=len(features.envelopes[FeatureKey.PITCH].items),
            instruments=1,
        )
