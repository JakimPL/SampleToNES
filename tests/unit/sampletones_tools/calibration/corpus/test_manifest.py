from pathlib import Path
from typing import Final, Optional

import numpy as np
import pytest
import yaml

from sampletones_core.audio import write_wave
from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from sampletones_tools.calibration.config.manifest import CorpusManifest
from sampletones_tools.calibration.corpus.families import Family
from sampletones_tools.calibration.corpus.manifest import (
    MissingPieceError,
    build_pieces,
    build_recordings,
    pieces_catalog,
    recordings_catalog,
)

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
        heard, kept = build_pieces(Config(), manifest=_manifest(nesmdb_archive(tmp_path, MEMBER), MEMBER))

        assert (heard.category, heard.listed) == ("nesmdb-review", True)
        assert (kept.category, kept.listed) == ("nesmdb-held-out", False)
        assert heard.family is Family.SEQUENCES
        assert heard.truth is not None and heard.truth.instructions

    def test_a_piece_the_archive_lacks_is_refused(self, tmp_path: Path) -> None:
        with pytest.raises(MissingPieceError, match="holds no piece"):
            build_pieces(Config(), manifest=_manifest(nesmdb_archive(tmp_path, MEMBER), "absent.mid"))

    def test_the_two_splits_are_categories_of_their_own(self, tmp_path: Path) -> None:
        catalog = pieces_catalog(_manifest(tmp_path / "unused.tar.gz", MEMBER))

        assert catalog == [(Family.SEQUENCES, "nesmdb-review"), (Family.SEQUENCES, "nesmdb-held-out")]


class TestBuildRecordings:
    def _manifest(self, tmp_path: Path, sources: int, stems: Optional[str]) -> CorpusManifest:
        for index in range(sources):
            write_wave(tmp_path / f"stem{index}.wav", 22050, np.full(2205, 0.1 * (index + 1), dtype=np.float32))
        setup = StemsConfig(
            entries=tuple(
                StemEntry(id=index, settings=StemSettings.covering([channel]))
                for index, channel in enumerate((ChannelName.PULSE1, ChannelName.NOISE))
            ),
            hierarchy=StemsHierarchy(levels=((0, 1),)),
        )
        (tmp_path / "setup.json").write_text(setup.model_dump_json(), encoding="utf-8")
        item = {
            "kind": "recording",
            "name": "song",
            "family": "composites",
            "category": "song",
            "listed": True,
            "sources": [f"stem{index}.wav" for index in range(sources)],
            "stems": stems,
        }
        path = tmp_path / "manifest.yaml"
        path.write_text(yaml.safe_dump({"items": [item]}), encoding="utf-8")
        return CorpusManifest.read(path)

    def test_recordings_under_a_setup_are_held_as_its_stems(self, tmp_path: Path) -> None:
        (song,) = build_recordings(Config(), manifest=self._manifest(tmp_path, 2, "setup.json"))

        assert song.stems is not None
        assert len(song.stems.sources) == 2
        assert song.channels == frozenset({ChannelName.PULSE1, ChannelName.NOISE})
        assert recordings_catalog(self._manifest(tmp_path, 2, "setup.json")) == [(Family.COMPOSITES, "song")]

    def test_a_setup_of_other_stems_than_its_recordings_is_refused(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="1 recordings for 2 stems"):
            build_recordings(Config(), manifest=self._manifest(tmp_path, 1, "setup.json"))
