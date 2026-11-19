from pathlib import Path
from typing import Final

import pytest

from sampletones_core.configs import Config
from sampletones_tools.calibration.config.manifest import CorpusManifest
from sampletones_tools.calibration.corpus.families import Family
from sampletones_tools.calibration.corpus.manifest import MissingPieceError, build_manifest, manifest_catalog

from ..midifiles import nesmdb_archive

MEMBER: Final[str] = "nesmdb_midi/train/piece.mid"


def _manifest(archive: Path, member: str) -> CorpusManifest:
    return CorpusManifest.model_validate(
        {
            "items": [
                {
                    "kind": "nesmdb",
                    "name": name,
                    "archive": str(archive),
                    "member": member,
                    "start_frame": 0,
                    "frames": 30,
                    "split": split,
                }
                for name, split in (("heard", "review"), ("kept", "held-out"))
            ]
        }
    )


class TestBuildManifest:
    def test_a_review_piece_is_listed_and_a_held_out_one_keeps_its_record_alone(self, tmp_path: Path) -> None:
        heard, kept = build_manifest(Config(), manifest=_manifest(nesmdb_archive(tmp_path, MEMBER), MEMBER))

        assert (heard.category, heard.listed) == ("nesmdb-review", True)
        assert (kept.category, kept.listed) == ("nesmdb-held-out", False)
        assert heard.family is Family.SEQUENCES
        assert heard.truth is not None and heard.truth.instructions

    def test_a_piece_the_archive_lacks_is_refused(self, tmp_path: Path) -> None:
        with pytest.raises(MissingPieceError, match="holds no piece"):
            build_manifest(Config(), manifest=_manifest(nesmdb_archive(tmp_path, MEMBER), "absent.mid"))

    def test_the_two_splits_are_categories_of_their_own(self, tmp_path: Path) -> None:
        catalog = manifest_catalog(_manifest(tmp_path / "unused.tar.gz", MEMBER))

        assert catalog == [(Family.SEQUENCES, "nesmdb-review"), (Family.SEQUENCES, "nesmdb-held-out")]
