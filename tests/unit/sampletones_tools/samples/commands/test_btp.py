from pathlib import Path
from typing import Final, List, Tuple

import pytest

from sampletones.commands.registry import COMMANDS
from sampletones.dispatcher import dispatch
from sampletones_tools.samples.bitphase import write_samples
from sampletones_tools.samples.emit import Emitter

EMITTER: Final[str] = "sampletones_tools.samples.emit.emit_samples"


class TestBtpSamples:
    def test_the_bitphase_emitter_writes_into_the_output_and_every_file_is_printed(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        calls: List[Tuple[Path, Emitter]] = []

        def emit_samples(output: Path, emitter: Emitter) -> List[Path]:
            calls.append((output, emitter))
            return [output / "drums.btp"]

        monkeypatch.setattr(EMITTER, emit_samples)

        assert dispatch(COMMANDS, ["btp", "samples", "-o", str(tmp_path)]) == 0
        assert calls == [(tmp_path, write_samples)]
        assert capsys.readouterr().out.splitlines() == [f"Wrote {tmp_path / 'drums.btp'}"]

    def test_the_output_is_required(self) -> None:
        with pytest.raises(SystemExit) as leaving:
            dispatch(COMMANDS, ["btp", "samples"])

        assert leaving.value.code == 2

    def test_an_action_is_required(self) -> None:
        with pytest.raises(SystemExit) as leaving:
            dispatch(COMMANDS, ["btp"])

        assert leaving.value.code == 2
