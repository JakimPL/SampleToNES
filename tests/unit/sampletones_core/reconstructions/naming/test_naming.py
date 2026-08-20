from pathlib import Path

from sampletones_core.reconstructions.naming.derive import derive_name


class TestDeriveName:
    def test_single_source_names_after_its_stem(self) -> None:
        assert derive_name((Path("/stems/kick.wav"),), fallback_stem="document") == "kick"

    def test_sources_sharing_one_directory_name_after_it(self) -> None:
        paths = (
            Path("/stems/drums/kick.wav"),
            Path("/stems/drums/snare.wav"),
        )

        assert derive_name(paths, fallback_stem="document") == "drums"

    def test_sources_from_different_directories_fall_back(self) -> None:
        paths = (
            Path("/a/kick.wav"),
            Path("/b/snare.wav"),
        )

        assert derive_name(paths, fallback_stem="document") == "document"

    def test_no_sources_fall_back(self) -> None:
        assert derive_name((), fallback_stem="document") == "document"
