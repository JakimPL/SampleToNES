from pathlib import Path
from unittest.mock import call, patch

from sampletones_shared.utils.system.reveal.grouped import (
    GroupedDirectoryBackend,
    distinct_parents,
)


class TestDistinctParents:
    def test_each_parent_once_in_first_seen_order(self) -> None:
        paths = (
            Path("/a/one.wav"),
            Path("/a/two.wav"),
            Path("/b/three.wav"),
            Path("/a/four.wav"),
        )

        assert distinct_parents(paths) == (Path("/a"), Path("/b"))

    def test_paths_in_one_directory_share_their_parent(self) -> None:
        paths = (Path("/a/one.wav"), Path("/a/two.wav"))

        assert distinct_parents(paths) == (Path("/a"),)


class TestGroupedDirectoryBackend:
    def test_opens_each_directory_once(self) -> None:
        paths = (
            Path("/a/one.wav"),
            Path("/a/two.wav"),
            Path("/b/three.wav"),
        )

        with patch("sampletones_shared.utils.system.reveal.grouped.open_path_in_explorer") as open_directory:
            GroupedDirectoryBackend().open(paths)

        assert open_directory.call_args_list == [call(Path("/a")), call(Path("/b"))]
