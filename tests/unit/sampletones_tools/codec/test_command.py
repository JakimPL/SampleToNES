from pathlib import Path
from typing import Final, List, Optional, Tuple

import pytest

from sampletones.commands.registry import COMMANDS
from sampletones.dispatcher import dispatch
from sampletones_tools.codec.study.manifest import StudyManifest

RUNNER: Final[str] = "sampletones_tools.codec.study.session.run_study"


class RecordedStudy:
    def __init__(self) -> None:
        self.runs: List[Tuple[StudyManifest, Optional[Path]]] = []

    def __call__(self, manifest: StudyManifest, output: Optional[Path]) -> Path:
        self.runs.append((manifest, output))
        return output if output is not None else Path("run")


class TestCodecStudy:
    def test_the_sources_and_the_sweep_are_read_from_the_options(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        study = RecordedStudy()
        monkeypatch.setattr(RUNNER, study)

        status = dispatch(
            COMMANDS,
            [
                "codec",
                "study",
                "--project",
                "songs/one.stp",
                "--reconstruction",
                "stems/two",
                "--variants",
                "wide-hold",
                "--lengthen",
                "30",
                "-o",
                str(tmp_path),
            ],
        )

        assert status == 0
        manifest, output = study.runs[0]
        assert [source.path for source in manifest.projects] == [Path("songs/one.stp")]
        assert [source.path for source in manifest.reconstructions] == [Path("stems/two")]
        assert manifest.variants == ("wide-hold",)
        assert manifest.lengthen_seconds == 30
        assert output == tmp_path

    def test_a_quick_run_reads_the_small_corpus_into_the_documents(self, monkeypatch: pytest.MonkeyPatch) -> None:
        study = RecordedStudy()
        monkeypatch.setattr(RUNNER, study)

        assert dispatch(COMMANDS, ["codec", "study", "--quick"]) == 0
        manifest, output = study.runs[0]
        assert manifest == StudyManifest.default(lengthen_seconds=180, variants=("all",), quick=True)
        assert output is None

    def test_an_action_is_required(self) -> None:
        with pytest.raises(SystemExit) as leaving:
            dispatch(COMMANDS, ["codec"])

        assert leaving.value.code == 2
