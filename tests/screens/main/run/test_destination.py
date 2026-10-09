from pathlib import Path
from typing import Dict, FrozenSet, List

from automation.screen import Screen
from automation.steps.main import gather, give_each_its_own_channel, home_path
from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions.reconstruction.reconstruction import Reconstruction
from sampletones_core.reconstructions.reconstruction.renders import rendered_channels
from sampletones_shared.paths.user import RECONSTRUCTIONS_DIRECTORY
from tests.screens.main.run.constants import ALBUM, ALBUM_TAKES, BASS, DISC, DISC_TAKES, LEAD, RECONSTRUCTION_SUFFIX
from tests.screens.main.run.steps import modified, run_to_its_end, written


def converted_channels(path: Path) -> FrozenSet[ChannelName]:
    """The channels a written reconstruction approximates, read off the file."""
    return frozenset(rendered_channels(Reconstruction.load(path)))


def written_as(path: Path) -> Path:
    """The one reconstruction a run wrote for the recording at ``path``, wherever below the folder it went."""
    found = [file for file in written(RECONSTRUCTIONS_DIRECTORY) if file.stem == path.stem]
    assert len(found) == 1, found
    return found[0]


class TestWhereARunWrites:
    """A run writes each recording with the channels its row gave, where the Destination line says."""

    def channels(self) -> Dict[Path, ChannelName]:
        """The channel each gathered recording is given: the bass Triangle, the lead Pulse 1."""
        return {home_path(BASS): ChannelName.TRIANGLE, home_path(LEAD): ChannelName.PULSE1}

    def test_each_recording_carries_the_channels_its_row_gave(self, screen: Screen) -> None:
        """Each written reconstruction approximates only the channel its recording was given."""
        gather(screen, home_path(BASS), home_path(LEAD))
        give_each_its_own_channel(screen, self.channels())

        run_to_its_end(screen)

        for path, channel in self.channels().items():
            assert converted_channels(written_as(path)) == {channel}

    def test_the_destination_line_names_the_folder_holding_what_the_run_writes(self, screen: Screen) -> None:
        """Each reconstruction lands in a folder of its own channels, and the Destination line names the
        folder holding both."""
        converter = screen.main.converter
        gather(screen, home_path(BASS), home_path(LEAD))
        give_each_its_own_channel(screen, self.channels())
        destination = Path(converter.destination())

        run_to_its_end(screen)

        folders = {written_as(path).parent for path in self.channels()}
        assert len(folders) == len(self.channels())
        assert all(folder.parent == destination for folder in folders)


class TestAFolderConverts:
    """A listed folder converts into a tree mirroring it; a rerun replaces nothing already written and
    makes the rest.

    The Album folder, with its nested Disc2 folder, is gathered and converted. One written file is then
    deleted and the run repeated; the deleted file returns and the others keep their modification times.
    """

    def test_a_mirrored_tree_then_only_what_is_missing(self, screen: Screen) -> None:
        converter = screen.main.converter
        folder = home_path(ALBUM)
        expected = [Path(name).with_suffix(RECONSTRUCTION_SUFFIX) for name in ALBUM_TAKES] + [
            (Path(DISC) / name).with_suffix(RECONSTRUCTION_SUFFIX) for name in DISC_TAKES
        ]
        kept: List[Dict[Path, int]] = []
        destinations: List[Path] = []

        def convert_the_folder(screen: Screen) -> None:
            gather(screen, folder)
            destinations.append(Path(converter.destination()))

            run_to_its_end(screen)

            files = written(destinations[0])
            assert len(files) == len(expected)
            assert all(any(file.as_posix().endswith(part.as_posix()) for file in files) for part in expected)

        def rerun_makes_only_what_is_missing(screen: Screen) -> None:
            files = written(destinations[0])
            missing, *standing = files
            missing.unlink()
            kept.append(modified(standing))

            run_to_its_end(screen)

            assert written(destinations[0]) == files
            assert modified(standing) == kept[0]

        screen.scenario(convert_the_folder, rerun_makes_only_what_is_missing).run()
