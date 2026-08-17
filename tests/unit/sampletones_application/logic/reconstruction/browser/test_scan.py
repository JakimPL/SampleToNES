from pathlib import Path

from sampletones_application.logic.reconstruction.browser.tree.entries.directory import (
    DirectoryEntry,
)
from sampletones_application.logic.reconstruction.browser.tree.entries.reconstruction import (
    ReconstructionEntry,
)
from sampletones_application.logic.reconstruction.browser.tree.scan import (
    scan_reconstructions,
)

from .conftest import config_directory, config_fields, write_reconstruction


class TestScanEntries:
    def test_reconstruction_file_becomes_an_entry_named_by_its_audio(self, tmp_path: Path) -> None:
        path = write_reconstruction(tmp_path, "song")

        scan = scan_reconstructions(tmp_path)

        assert scan.entries == (ReconstructionEntry(path=path),)
        assert scan.entries[0].name == "song"

    def test_other_files_stay_out(self, tmp_path: Path) -> None:
        (tmp_path / "audio.wav").touch()
        write_reconstruction(tmp_path, "song")

        scan = scan_reconstructions(tmp_path)

        assert [entry.path.name for entry in scan.entries] == ["song.stn"]

    def test_entries_follow_the_sorted_order_of_the_folder(self, tmp_path: Path) -> None:
        for name in ("charlie", "alpha", "bravo"):
            write_reconstruction(tmp_path, name)

        scan = scan_reconstructions(tmp_path)

        assert [entry.name for entry in scan.entries] == ["alpha", "bravo", "charlie"]

    def test_folder_becomes_an_entry_holding_what_is_inside(self, tmp_path: Path) -> None:
        path = write_reconstruction(tmp_path / "my_songs", "song")

        scan = scan_reconstructions(tmp_path)

        assert scan.entries == (
            DirectoryEntry(
                path=tmp_path / "my_songs",
                config=None,
                entries=(ReconstructionEntry(path=path),),
            ),
        )

    def test_empty_folder_becomes_an_entry_holding_nothing(self, tmp_path: Path) -> None:
        (tmp_path / "empty").mkdir()

        scan = scan_reconstructions(tmp_path)

        assert scan.entries == (DirectoryEntry(path=tmp_path / "empty", config=None, entries=()),)


class TestScanConfiguration:
    def test_config_directory_states_the_configuration_its_name_encodes(self, tmp_path: Path) -> None:
        fields = config_fields()
        config_directory(tmp_path, fields)

        scan = scan_reconstructions(tmp_path)

        assert [entry.config for entry in scan.entries] == [fields]

    def test_plain_folder_states_no_configuration(self, tmp_path: Path) -> None:
        (tmp_path / "my_songs").mkdir()

        scan = scan_reconstructions(tmp_path)

        assert [entry.config for entry in scan.entries] == [None]

    def test_nested_config_directory_states_its_configuration(self, tmp_path: Path) -> None:
        fields = config_fields()
        config_directory(tmp_path / "my_songs", fields)

        scan = scan_reconstructions(tmp_path)

        nested = scan.entries[0]
        assert isinstance(nested, DirectoryEntry)
        assert [entry.config for entry in nested.entries] == [fields]


class TestScanReconstructions:
    def test_collects_every_reconstruction_beneath_the_directory(self, tmp_path: Path) -> None:
        root_path = write_reconstruction(tmp_path, "song")
        nested_path = write_reconstruction(tmp_path / "sub" / "deeper", "track")

        scan = scan_reconstructions(tmp_path)

        assert {entry.path for entry in scan.reconstructions} == {root_path, nested_path}

    def test_collects_nothing_from_an_empty_directory(self, tmp_path: Path) -> None:
        assert scan_reconstructions(tmp_path).reconstructions == ()

    def test_directory_entry_collects_the_reconstructions_beneath_it(self, tmp_path: Path) -> None:
        fields = config_fields()
        directory = config_directory(tmp_path, fields)
        nested_path = write_reconstruction(directory, "Amen Breaks", "cw_amen02_165")
        write_reconstruction(tmp_path, "outside")

        scan = scan_reconstructions(tmp_path)

        config_entry = next(entry for entry in scan.entries if isinstance(entry, DirectoryEntry))
        assert [entry.path for entry in scan.collect_reconstructions(config_entry.entries)] == [nested_path]
