from pathlib import Path
from typing import Final, List, Tuple

import pytest

from sampletones.commands.registry import COMMANDS
from sampletones.dispatcher import dispatch
from sampletones_tools.samples.emit import Emitter
from sampletones_tools.samples.rom import write_samples

EMITTER: Final[str] = "sampletones_tools.samples.emit.emit_samples"


class TestRomSamples:
    def test_the_cartridge_emitter_writes_into_the_output_and_every_file_is_printed(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        calls: List[Tuple[Path, Emitter]] = []

        def emit_samples(output: Path, emitter: Emitter) -> List[Path]:
            calls.append((output, emitter))
            return [output / "kick.nes", output / "song.nes"]

        monkeypatch.setattr(EMITTER, emit_samples)

        assert dispatch(COMMANDS, ["rom", "samples", "--output", str(tmp_path)]) == 0
        assert calls == [(tmp_path, write_samples)]
        assert capsys.readouterr().out.splitlines() == [
            f"Wrote {tmp_path / 'kick.nes'}",
            f"Wrote {tmp_path / 'song.nes'}",
        ]

    def test_the_output_is_required(self) -> None:
        with pytest.raises(SystemExit) as leaving:
            dispatch(COMMANDS, ["rom", "samples"])

        assert leaving.value.code == 2
