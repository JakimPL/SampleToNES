from typing import Dict, Final
from unittest.mock import MagicMock, patch

from sampletones_application.logic.instruction.table import InstructionTableLogic
from sampletones_application.view_model.instruction.table_data import InstructionTableData
from sampletones_core.instructions.implementation.noise import NoiseInstruction
from sampletones_core.instructions.implementation.pulse import PulseInstruction
from tests.suite.language import FakeLanguageManager

FIRST_ARGUMENT: Final[str] = "{0}"

TEXTS: Final[Dict[str, str]] = {
    "instructions.details.template.frequency_template": FIRST_ARGUMENT,
    "instructions.details.template.pitch_template": FIRST_ARGUMENT,
    "instructions.details.template.duty_cycle_template": FIRST_ARGUMENT,
    "instructions.details.template.period_template": FIRST_ARGUMENT,
    "global.dialog.label.yes": "yes",
    "global.dialog.label.no": "no",
}


def _logic() -> InstructionTableLogic:
    return InstructionTableLogic(
        language_manager=FakeLanguageManager(TEXTS),  # type: ignore[arg-type]
        float_precision=2,
    )


def _inject_data(
    logic: InstructionTableLogic,
    instruction,
    *,
    nes_frequency: int = 60,
    has_fragment: bool = False,
) -> None:
    data = MagicMock()
    data.instruction = instruction
    data.generator_class_name = "PulseGenerator"
    if has_fragment:
        fragment = MagicMock()
        fragment.__bool__ = lambda self: True
        fragment.generator_class = "pulse_generator"
        fragment.frequency = 440.0
        fragment.length = 512
        data.fragment = fragment
    else:
        data.fragment = None

    logic._current_data = data
    logic._current_nes_frequency = nes_frequency


def _pulse(
    pitch: int = 60,
    volume: int = 15,
    duty_cycle: int = 1,
) -> PulseInstruction:
    return PulseInstruction(
        on=True,
        pitch=pitch,
        volume=volume,
        duty_cycle=duty_cycle,
    )


def _noise(
    period: int = 3,
    volume: int = 10,
    short: bool = False,
) -> NoiseInstruction:
    return NoiseInstruction(
        on=volume > 0,
        period=period,
        volume=volume,
        short=short,
    )


class TestInstructionTableLogicGetTableData:
    def test_no_data_returns_none(self) -> None:
        logic = _logic()
        assert logic.get_table_data() is None

    def test_with_data_without_fragment_returns_table_data(self) -> None:
        logic = _logic()
        _inject_data(logic, _pulse())
        result = logic.get_table_data()
        assert isinstance(result, InstructionTableData)

    def test_without_fragment_general_rows_have_three_entries(self) -> None:
        logic = _logic()
        _inject_data(logic, _pulse(), has_fragment=False)
        result = logic.get_table_data()
        assert result is not None
        assert len(result.general_rows) == 3

    def test_with_fragment_general_rows_have_four_entries(self) -> None:
        logic = _logic()
        _inject_data(logic, _pulse(), has_fragment=True)
        result = logic.get_table_data()
        assert result is not None
        assert len(result.general_rows) == 4

    def test_clear_data_makes_get_table_data_return_none(self) -> None:
        logic = _logic()
        _inject_data(logic, _pulse())
        logic.clear_data()
        assert logic.get_table_data() is None


class TestInstructionTableLogicParameterFormatting:
    def test_pitch_parameter_formatted_as_note_name(self) -> None:
        logic = _logic()
        _inject_data(logic, _pulse(pitch=60))
        result = logic.get_table_data()
        assert result is not None
        pitch_row = next(row for row in result.parameter_rows if row.label == "pitch")
        assert "C" in pitch_row.value

    def test_duty_cycle_parameter_formatted_as_percentage(self) -> None:
        logic = _logic()
        _inject_data(logic, _pulse(duty_cycle=1))
        result = logic.get_table_data()
        assert result is not None
        duty_row = next(row for row in result.parameter_rows if row.label == "duty_cycle")
        assert "25" in duty_row.value

    def test_boolean_on_parameter_formatted_as_yes(self) -> None:
        logic = _logic()
        _inject_data(
            logic,
            PulseInstruction(
                on=True,
                pitch=60,
                volume=15,
                duty_cycle=0,
            ),
        )
        result = logic.get_table_data()
        assert result is not None
        on_row = next(row for row in result.parameter_rows if row.label == "on")
        assert on_row.value == "yes"

    def test_boolean_off_parameter_formatted_as_no(self) -> None:
        logic = _logic()
        _inject_data(
            logic,
            PulseInstruction(
                on=False,
                pitch=60,
                volume=0,
                duty_cycle=0,
            ),
        )
        result = logic.get_table_data()
        assert result is not None
        on_row = next(row for row in result.parameter_rows if row.label == "on")
        assert on_row.value == "no"

    def test_period_parameter_formatted_with_noise_period_value(self) -> None:
        logic = _logic()
        _inject_data(logic, _noise(period=0))
        result = logic.get_table_data()
        assert result is not None
        period_row = next(row for row in result.parameter_rows if row.label == "period")
        assert period_row.value != ""

    def test_volume_parameter_formatted_as_integer_string(self) -> None:
        logic = _logic()
        _inject_data(logic, _pulse(volume=15))
        result = logic.get_table_data()
        assert result is not None
        volume_row = next(row for row in result.parameter_rows if row.label == "volume")
        assert volume_row.value == "15"


class TestInstructionTableLogicHashTracking:
    def test_current_hash_is_empty_initially(self) -> None:
        logic = _logic()
        assert logic.current_hash == ""

    def test_current_hash_set_after_assigning_data(self) -> None:
        logic = _logic()
        data = MagicMock()
        data.config.nes_frequency = 60
        with patch(
            "sampletones_application.logic.instruction.table.hash_model",
            return_value="deadbeef",
        ):
            logic.current_data = data

        assert logic.current_hash == "deadbeef"

    def test_clear_data_resets_hash_to_empty(self) -> None:
        logic = _logic()
        logic._current_data = MagicMock()
        logic._current_hash = "somehash"
        logic.clear_data()
        assert logic.current_hash == ""

    def test_current_nes_frequency_is_none_initially(self) -> None:
        logic = _logic()
        assert logic.current_nes_frequency is None

    def test_current_nes_frequency_set_after_assigning_data(self) -> None:
        logic = _logic()
        data = MagicMock()
        data.config.nes_frequency = 50
        with patch(
            "sampletones_application.logic.instruction.table.hash_model",
            return_value="hash",
        ):
            logic.current_data = data

        assert logic.current_nes_frequency == 50

    def test_clear_data_resets_nes_frequency_to_none(self) -> None:
        logic = _logic()
        logic._current_nes_frequency = 60
        logic.clear_data()
        assert logic.current_nes_frequency is None
