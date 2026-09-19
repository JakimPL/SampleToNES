import json
from pathlib import Path
from typing import Any, Dict, Final, List

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.formats.bitphase.model.instrument import BitphaseInstrumentPreset
from sampletones_core.formats.bitphase.notes import pitch_to_note_index
from sampletones_core.formats.bitphase.preset import (
    PRESET_TUNING_TABLE,
    instrument_to_preset,
    write_preset,
)
from sampletones_core.formats.bitphase.specification.chip import CHIP_TYPE_NES
from sampletones_core.formats.bitphase.specification.instruments import (
    LOOP_FROM_START,
    MAX_TONE_ADD,
    MIN_TONE_ADD,
    NO_TONE_OFFSET,
)
from sampletones_core.formats.bitphase.specification.macros import NesMacroField
from sampletones_shared.paths.extensions import EXT_FILE_JSON

from .conftest import REFERENCE_PITCH, build_features, build_instrument

VOLUME_ENVELOPE: Final[List[int]] = [15, 10, 5, 0]
PITCH_CONTOUR: Final[List[int]] = [0, 3, 7, 12]
NOISE_PERIOD: Final[int] = 4
PRESET_KEYS: Final[List[str]] = ["chipType", "name", "macros"]


def levels(preset: BitphaseInstrumentPreset) -> List[int]:
    return list(preset.macros[NesMacroField.VOLUME_OR_RATE].values)


def offsets(preset: BitphaseInstrumentPreset) -> List[int]:
    return list(preset.macros[NesMacroField.TONE_ADD].values)


@pytest.fixture(name="preset")
def preset_fixture() -> BitphaseInstrumentPreset:
    return instrument_to_preset(
        build_instrument("Lead", build_features(VOLUME_ENVELOPE, arpeggio=PITCH_CONTOUR)),
    )


@pytest.fixture(name="document")
def document_fixture(preset: BitphaseInstrumentPreset, tmp_path: Path) -> Dict[str, Any]:
    destination = tmp_path / f"Lead{EXT_FILE_JSON}"
    write_preset(destination, preset)
    return json.loads(destination.read_text(encoding="utf-8"))


class TestThePresetCarriesTheSlice:
    def test_it_takes_the_slice_name(self, preset: BitphaseInstrumentPreset) -> None:
        assert preset.name == "Lead"

    def test_it_holds_one_level_per_envelope_item(self, preset: BitphaseInstrumentPreset) -> None:
        assert levels(preset) == VOLUME_ENVELOPE

    def test_a_one_shot_holds_its_final_value(self, preset: BitphaseInstrumentPreset) -> None:
        assert all(macro.loop == len(macro.values) - 1 for macro in preset.macros.values())

    def test_a_looping_slice_circles_from_its_first_value(self) -> None:
        preset = instrument_to_preset(
            build_instrument("Pad", build_features(VOLUME_ENVELOPE), loop_point=0),
        )
        assert preset.macros[NesMacroField.VOLUME_OR_RATE].loop == LOOP_FROM_START


class TestThePitchContourRidesInTheToneOffset:
    """A preset carries macros alone, so the movement a table would drive is expressed as
    the per-tick period offset each tick adds to the note's own period.
    """

    def test_each_tick_offsets_the_period_its_semitone_asks_for(self, preset: BitphaseInstrumentPreset) -> None:
        base_index = pitch_to_note_index(REFERENCE_PITCH)
        base_period = PRESET_TUNING_TABLE[base_index]
        expected = [PRESET_TUNING_TABLE[base_index + semitones] - base_period for semitones in PITCH_CONTOUR]
        assert offsets(preset) == expected

    def test_the_first_tick_plays_the_reconstructed_pitch(self, preset: BitphaseInstrumentPreset) -> None:
        assert offsets(preset)[0] == NO_TONE_OFFSET

    def test_a_rising_contour_shortens_the_period(self, preset: BitphaseInstrumentPreset) -> None:
        written = offsets(preset)
        assert all(later <= earlier for earlier, later in zip(written, written[1:]))

    def test_every_offset_fits_the_field(self, preset: BitphaseInstrumentPreset) -> None:
        assert all(MIN_TONE_ADD <= offset <= MAX_TONE_ADD for offset in offsets(preset))

    def test_a_contour_reaching_past_the_tuning_table_holds_its_edge(self) -> None:
        preset = instrument_to_preset(
            build_instrument("Sweep", build_features(VOLUME_ENVELOPE, arpeggio=[0, 40, 80, 120])),
        )
        assert all(MIN_TONE_ADD <= offset <= MAX_TONE_ADD for offset in offsets(preset))

    def test_a_noise_slice_takes_its_period_from_the_note(self) -> None:
        preset = instrument_to_preset(
            build_instrument(
                "Hat",
                build_features(VOLUME_ENVELOPE, arpeggio=[0, 1, 2, 3], initial_pitch=NOISE_PERIOD),
                channel=ChannelName.NOISE,
            ),
        )
        assert set(offsets(preset)) == {NO_TONE_OFFSET}


class TestThePresetFile:
    @pytest.mark.parametrize("key", PRESET_KEYS)
    def test_it_holds_every_field_the_panel_reads(self, document: Dict[str, Any], key: str) -> None:
        assert key in document

    def test_it_names_the_chip_whose_fields_it_holds(self, document: Dict[str, Any]) -> None:
        assert document["chipType"] == CHIP_TYPE_NES

    def test_it_is_indented_the_way_bitphase_writes_its_own(
        self, preset: BitphaseInstrumentPreset, tmp_path: Path
    ) -> None:
        destination = tmp_path / f"Lead{EXT_FILE_JSON}"
        write_preset(destination, preset)
        assert '\n  "name"' in destination.read_text(encoding="utf-8")

    def test_its_macros_carry_the_field_names_the_panel_reads(self, document: Dict[str, Any]) -> None:
        assert {"pulseWidth", "volumeOrRate", "toneAdd"} <= set(document["macros"])

    def test_each_macro_carries_its_values_and_the_point_they_circle_from(self, document: Dict[str, Any]) -> None:
        assert all(set(macro) == {"values", "loop"} for macro in document["macros"].values())
