from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from sampletones_tools.calibration.config.manifest import CorpusManifest, Split

PIECE = {
    "kind": "nesmdb",
    "name": "piece",
    "archive": "archives/nesmdb.tar.gz",
    "member": "nesmdb_midi/train/piece.mid",
    "start_frame": 0,
    "frames": 120,
    "split": "review",
}


class TestCorpusManifest:
    def test_an_archive_is_found_beside_the_manifest(self, tmp_path: Path) -> None:
        path = tmp_path / "manifest.yaml"
        path.write_text(yaml.safe_dump({"items": [PIECE]}), encoding="utf-8")

        (item,) = CorpusManifest.read(path).items

        assert item.archive == tmp_path / "archives" / "nesmdb.tar.gz"
        assert item.split is Split.REVIEW

    def test_two_sounds_of_one_name_are_refused(self) -> None:
        with pytest.raises(ValidationError, match="name of its own"):
            CorpusManifest.model_validate({"items": [PIECE, PIECE]})


class TestRecordingItem:
    RECORDING = {"kind": "recording", "name": "song", "family": "composites", "category": "song", "listed": True}

    def test_every_recording_and_its_setup_are_found_beside_the_manifest(self, tmp_path: Path) -> None:
        path = tmp_path / "manifest.yaml"
        item = {**self.RECORDING, "sources": ["a.wav", "b.wav"], "stems": "setup.json"}
        path.write_text(yaml.safe_dump({"items": [item]}), encoding="utf-8")

        (recording,) = CorpusManifest.read(path).recordings

        assert recording.sources == [tmp_path / "a.wav", tmp_path / "b.wav"]
        assert recording.stems == tmp_path / "setup.json"

    def test_several_recordings_without_a_setup_are_refused(self) -> None:
        with pytest.raises(ValidationError, match="no stems setup"):
            CorpusManifest.model_validate({"items": [{**self.RECORDING, "sources": ["a.wav", "b.wav"], "stems": None}]})
