from typing import Any, Dict

from sampletones_core.compatibility.fields import (
    AUDIO_FILEPATH,
    CHANNEL_NAME,
    CHANNELS,
    GENERATOR_NAME,
    INSTRUCTIONS,
    STEMS_DATA,
)
from sampletones_core.compatibility.reconstruction.v2_2 import update
from sampletones_core.constants.algorithm import DEFAULT_STEMS_CHANNEL_CAP


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

    def test_stamps_the_embedded_config_metadata(self) -> None:
        data = {"config": {"metadata": {"reconstruction_data_version": "2.1"}}}

        upgraded = update(data)

        assert upgraded["config"]["metadata"]["reconstruction_data_version"] == "2.2"

    def test_leaves_the_input_untouched(self) -> None:
        data = {
            "approximations_data": [{GENERATOR_NAME: "pulse1"}],
            "instructions_data": [_stream({})],
        }

        update(data)

        assert data["approximations_data"][0][GENERATOR_NAME] == "pulse1"
        assert data["instructions_data"][0][GENERATOR_NAME] == "pulse1"

    def test_payload_without_known_sections_gains_the_stems_record(self) -> None:
        data = {"id": "abc"}

        upgraded = update(data)

        assert upgraded["id"] == "abc"
        assert upgraded[AUDIO_FILEPATH] == []
        assert upgraded[STEMS_DATA]["config"]["entries"][0]["channels"] == []
        assert upgraded[STEMS_DATA]["assignments"] == []

    def test_a_single_path_records_as_a_one_tuple(self) -> None:
        data = {AUDIO_FILEPATH: "/audio/kick.wav"}

        upgraded = update(data)

        assert upgraded[AUDIO_FILEPATH] == ["/audio/kick.wav"]

    def test_a_file_without_stems_data_gains_the_single_entry_record(self) -> None:
        data = {
            "config": {"generation": {"channels": ["pulse1", "noise"]}},
            "instructions_data": [
                {CHANNEL_NAME: "pulse1", INSTRUCTIONS: ["frame", "frame"]},
                {CHANNEL_NAME: "noise", INSTRUCTIONS: []},
            ],
        }

        upgraded = update(data)

        stems_data = upgraded[STEMS_DATA]
        assert stems_data["config"]["entries"] == [{"id": 0, CHANNELS: ["pulse1", "noise"]}]
        assert stems_data["config"]["channel_cap"] == DEFAULT_STEMS_CHANNEL_CAP
        assert stems_data["assignments"] == [
            {CHANNEL_NAME: "pulse1", "stem_ids": [0, 0]},
        ]
