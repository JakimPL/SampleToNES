from typing import Any, Dict

from sampletones_core.compatibility.fields import CHANNEL_NAME, GENERATOR_NAME
from sampletones_core.compatibility.reconstruction.v2_2 import update


def _stream(extra: Dict[str, Any]) -> Dict[str, Any]:
    return {GENERATOR_NAME: "pulse1", "instructions": [], **extra}


class TestReconstructionV2_2:
    def test_renames_approximation_entries(self) -> None:
        data = {"approximations_data": [{GENERATOR_NAME: "pulse1", "approximation": [1.0, 2.0]}]}

        upgraded = update(data)

        assert upgraded["approximations_data"][0][CHANNEL_NAME] == "pulse1"
        assert GENERATOR_NAME not in upgraded["approximations_data"][0]

    def test_renames_instruction_entries(self) -> None:
        data = {"instructions_data": [_stream({})]}

        upgraded = update(data)

        assert upgraded["instructions_data"][0][CHANNEL_NAME] == "pulse1"
        assert GENERATOR_NAME not in upgraded["instructions_data"][0]

    def test_renames_embedded_channel_selection(self) -> None:
        data = {"config": {"generation": {"generators": ["pulse1", "noise"], "drive": 1.0}}}

        upgraded = update(data)

        assert upgraded["config"]["generation"]["channels"] == ["pulse1", "noise"]
        assert "generators" not in upgraded["config"]["generation"]

    def test_leaves_the_input_untouched(self) -> None:
        data = {
            "approximations_data": [{GENERATOR_NAME: "pulse1"}],
            "instructions_data": [_stream({})],
        }

        update(data)

        assert data["approximations_data"][0][GENERATOR_NAME] == "pulse1"
        assert data["instructions_data"][0][GENERATOR_NAME] == "pulse1"

    def test_payload_without_known_sections_stays_the_same_shape(self) -> None:
        data = {"id": "abc"}

        assert update(data) == data
