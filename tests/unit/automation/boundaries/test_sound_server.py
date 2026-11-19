import shutil
from pathlib import Path

import pytest

from automation.boundaries import sound_server
from automation.boundaries.sound_server import (
    PULSEAUDIO,
    SOCKET_FILE,
    UNIX_ADDRESS_PREFIX,
    SoundServer,
    SoundServerMissingError,
)
from tests.suite.base import BaseTestSuite

INSTALLED = shutil.which(PULSEAUDIO) is not None


class TestTheWorkersSoundServer(BaseTestSuite):
    """A PulseAudio server of the worker's own, reached at a socket inside its folder."""

    def test_its_address_is_the_socket_in_its_folder(self, tmp_path: Path) -> None:
        assert SoundServer(tmp_path).address == f"{UNIX_ADDRESS_PREFIX}{tmp_path / SOCKET_FILE}"

    def test_a_machine_without_pulseaudio_is_told_what_to_install(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(sound_server.shutil, "which", lambda program: None)

        with pytest.raises(SoundServerMissingError, match=PULSEAUDIO):
            SoundServer(tmp_path).start()

    @pytest.mark.skipif(not INSTALLED, reason=f"{PULSEAUDIO} is not installed on this machine")
    def test_a_started_server_opens_its_socket_and_a_stopped_one_closes_it(self, tmp_path: Path) -> None:
        server = SoundServer(tmp_path / "sound")

        address = server.start()
        try:
            assert address == server.address
            assert (tmp_path / "sound" / SOCKET_FILE).exists()
        finally:
            server.stop()

        assert not (tmp_path / "sound" / SOCKET_FILE).exists()

    def test_stopping_a_server_never_started_does_nothing(self, tmp_path: Path) -> None:
        SoundServer(tmp_path).stop()
