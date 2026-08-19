from typing import Any, Dict

from sampletones_core.compatibility.fields import CHANNEL_NAME
from sampletones_core.compatibility.project.v1_1 import update


def _pool(extra: Dict[str, Any]) -> Dict[str, Any]:
    return {"generator": "pulse1", "patterns": {}, **extra}


class TestProjectV1_1:
    def test_renames_channel_pool_field(self) -> None:
        data = {"song": {"channels": {"pulse1": _pool({})}}}

        upgraded = update(data)

        assert upgraded["song"]["channels"]["pulse1"][CHANNEL_NAME] == "pulse1"
        assert "generator" not in upgraded["song"]["channels"]["pulse1"]

    def test_renames_instrument_command_channel(self) -> None:
        data = {
            "song": {
                "channels": {
                    "pulse1": {
                        "generator": "pulse1",
                        "patterns": {
                            "0": {
                                "rows": {
                                    "0": {
                                        "command": {
                                            "sample_id": "s",
                                            "generator_name": "pulse1",
                                        }
                                    },
                                }
                            }
                        },
                    }
                }
            }
        }

        upgraded = update(data)

        command = upgraded["song"]["channels"]["pulse1"]["patterns"]["0"]["rows"]["0"]["command"]
        assert command[CHANNEL_NAME] == "pulse1"
        assert "generator_name" not in command

    def test_leaves_note_off_commands_untouched(self) -> None:
        data = {
            "song": {
                "channels": {
                    "pulse1": {
                        "generator": "pulse1",
                        "patterns": {
                            "0": {
                                "rows": {
                                    "0": {
                                        "command": {},
                                    }
                                }
                            }
                        },
                    }
                }
            }
        }

        upgraded = update(data)

        command = upgraded["song"]["channels"]["pulse1"]["patterns"]["0"]["rows"]["0"]["command"]
        assert command == {}

    def test_leaves_the_input_untouched(self) -> None:
        data = {"song": {"channels": {"pulse1": _pool({})}}}

        update(data)

        assert data["song"]["channels"]["pulse1"]["generator"] == "pulse1"

    def test_document_without_a_song_stays_the_same_shape(self) -> None:
        data = {"format_version": "1.0"}

        assert update(data) == data
