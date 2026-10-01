from enum import StrEnum
from pathlib import Path
from typing import Final

import pyaudio
import pytest

ALSA_CONFIGURATION_FILE: Final[str] = ".asoundrc"
SILENT_DEFAULT_DEVICE: Final[str] = "pcm.!default {\n    type null\n}\n"


class OutputDevice(StrEnum):
    """The output a scenario's machine offers: a device that plays into silence, or none at all."""

    SILENT = "silent"
    NONE = "none"


def provide_output_device(
    device: OutputDevice,
    *,
    home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Gives the application the output ``device`` before it starts."""
    match device:
        case OutputDevice.SILENT:
            _silent_output_device(home)
        case OutputDevice.NONE:
            _no_output_device(monkeypatch)


def _silent_output_device(home: Path) -> None:
    """Points ALSA's default device at a sink that consumes sound in real time and plays none of it.

    Playback runs as it does for a user, its stream and its cursor included, and nothing is heard.
    """
    (home / ALSA_CONFIGURATION_FILE).write_text(SILENT_DEFAULT_DEVICE, encoding="utf-8")


def _no_output_device(monkeypatch: pytest.MonkeyPatch) -> None:
    """Starts the application on a machine offering no output device at all."""
    monkeypatch.setattr(pyaudio.PyAudio, "get_device_count", lambda _: 0)
    monkeypatch.setattr(pyaudio.PyAudio, "get_default_output_device_info", _no_default_device)


def _no_default_device(_: pyaudio.PyAudio) -> None:
    raise OSError("A screen scenario offers no output device")
