import pytest

from sampletones_application.utils.midi import select_midi_backend
from sampletones_application.utils.midi.backends.alsa import AlsaMidiBackend
from sampletones_application.utils.midi.backends.portmidi import PortMidiBackend
from sampletones_shared.utils.system.system import System


class TestSelection:
    """Each system is read through its own MIDI service, and choosing a backend loads no library."""

    def test_linux_reads_the_alsa_sequencer(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(System, "current", classmethod(lambda cls: System.LINUX))

        assert isinstance(select_midi_backend(), AlsaMidiBackend)

    @pytest.mark.parametrize("system", [System.WINDOWS, System.MACOS])
    def test_windows_and_macos_read_portmidi(self, system: System, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(System, "current", classmethod(lambda cls: system))

        assert isinstance(select_midi_backend(), PortMidiBackend)
