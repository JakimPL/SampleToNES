from pathlib import Path

import pytest

from sampletones_core.reconstructions.naming.derive import derive_name


class TestDeriveName:
    def test_single_source_names_after_its_stem(self) -> None:
        assert derive_name((Path("/stems/kick.wav"),)) == "kick"

    def test_sources_sharing_one_directory_name_after_it(self) -> None:
        paths = (
            Path("/stems/drums/kick.wav"),
            Path("/stems/drums/snare.wav"),
        )

        assert derive_name(paths) == "drums"

    def test_sources_sharing_a_filename_prefix_name_after_it(self) -> None:
        paths = (
            Path("/a/song_vocals.wav"),
            Path("/b/song_drums.wav"),
        )

        assert derive_name(paths) == "song"

    def test_sources_with_matching_filenames_name_after_them(self) -> None:
        paths = (
            Path("/a/kick.wav"),
            Path("/b/kick.wav"),
        )

        assert derive_name(paths) == "kick"

    def test_sources_sharing_no_directory_name_after_the_first_stem(self) -> None:
        paths = (
            Path("/a/kick.wav"),
            Path("/b/snare.wav"),
        )

        assert derive_name(paths) == "kick"

    def test_no_sources_raise(self) -> None:
        with pytest.raises(ValueError, match="at least one"):
            derive_name(())
