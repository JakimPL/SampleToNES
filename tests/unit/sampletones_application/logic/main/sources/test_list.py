from pathlib import Path

from sampletones_application.logic.main.sources.key import SourceKey
from sampletones_application.logic.main.sources.list import SourceList
from sampletones_application.logic.main.sources.slots import BEND_SLOT, CHANNEL_SLOT
from sampletones_application.view_model.shared.agreement import Agreement
from sampletones_core.constants.enums import ChannelName
from tests.suite.base import BaseTestSuite
from tests.unit.sampletones_application.logic.main.sources.factories import folder, recording


class TestGatheringRecordings(BaseTestSuite):
    def test_a_recording_named_stands_as_a_row_of_its_own(self) -> None:
        sources = SourceList().add_recording(recording("/audio/a.wav"))
        assert sources.paths == (Path("/audio/a.wav"),)
        assert sources.row_count == 1

    def test_rows_stand_in_the_order_they_were_added(self) -> None:
        sources = SourceList().add_recording(recording("/audio/b.wav")).add_recording(recording("/audio/a.wav"))
        assert sources.paths == (Path("/audio/b.wav"), Path("/audio/a.wav"))

    def test_a_path_already_standing_leaves_the_list_as_it_is(self) -> None:
        first = recording("/audio/a.wav", [ChannelName.PULSE1])
        again = recording("/audio/a.wav", [ChannelName.NOISE])
        sources = SourceList().add_recording(first).add_recording(again)
        assert sources.rows == (first,)


class TestGatheringAFolder(BaseTestSuite):
    def test_a_folder_stands_as_one_row_holding_its_recordings(self) -> None:
        gathered = folder("/audio", [recording("/audio/a.wav"), recording("/audio/b.wav")])
        sources = SourceList().add_folder(gathered)

        assert sources.row_count == 1
        assert sources.count == 2
        assert sources.paths == (Path("/audio/a.wav"), Path("/audio/b.wav"))

    def test_a_root_already_standing_leaves_the_list_as_it_is(self) -> None:
        gathered = folder("/audio", [recording("/audio/a.wav")])
        sources = SourceList().add_folder(gathered).add_folder(folder("/audio", [recording("/audio/b.wav")]))
        assert sources.count == 1

    def test_a_loose_recording_the_folder_covers_joins_it(self) -> None:
        sources = SourceList().add_recording(recording("/audio/a.wav"))
        sources = sources.add_folder(folder("/audio", [recording("/audio/a.wav"), recording("/audio/b.wav")]))

        assert sources.row_count == 1
        assert sources.folder_root_of(Path("/audio/a.wav")) == Path("/audio")

    def test_a_loose_recording_joins_holding_the_settings_it_stood_with(self) -> None:
        settled = recording("/audio/a.wav", [ChannelName.NOISE])
        sources = SourceList().add_recording(settled)
        sources = sources.add_folder(folder("/audio", [recording("/audio/a.wav", [ChannelName.PULSE1])]))

        gathered = sources.recording(Path("/audio/a.wav"))
        assert gathered is not None
        assert gathered.settings.channel_set == {ChannelName.NOISE}

    def test_a_recording_another_folder_holds_stays_where_it_is(self) -> None:
        sources = SourceList().add_folder(folder("/audio/inner", [recording("/audio/inner/a.wav")]))
        sources = sources.add_folder(folder("/audio", [recording("/audio/inner/a.wav"), recording("/audio/b.wav")]))

        assert sources.folder_root_of(Path("/audio/inner/a.wav")) == Path("/audio/inner")
        assert sources.folder_root_of(Path("/audio/b.wav")) == Path("/audio")
        assert sources.count == 2

    def test_a_recording_the_reader_named_belongs_to_no_folder(self) -> None:
        sources = SourceList().add_recording(recording("/audio/a.wav"))
        assert sources.folder_root_of(Path("/audio/a.wav")) is None


class TestAFolderStandingForNothing(BaseTestSuite):
    """A row names the recordings a run writes, so a folder naming none stays out of the list."""

    def test_an_empty_folder_leaves_the_list_as_it_is(self) -> None:
        sources = SourceList().add_folder(folder("/audio", []))

        assert sources.rows == ()

    def test_a_folder_whose_recordings_another_holds_leaves_it_as_it_is(self) -> None:
        held = recording("/audio/takes/a.wav")
        sources = SourceList().add_folder(folder("/audio/takes", [held]))

        sources = sources.add_folder(folder("/audio/takes/again", [held]))

        assert sources.row_count == 1


class TestLettingSourcesGo(BaseTestSuite):
    def test_a_folder_goes_with_everything_it_holds(self) -> None:
        gathered = folder("/audio", [recording("/audio/a.wav"), recording("/audio/b.wav")])
        sources = SourceList().add_folder(gathered).remove(gathered.key)
        assert sources.rows == ()

    def test_a_recording_inside_a_folder_goes_from_that_folder(self) -> None:
        gathered = folder("/audio", [recording("/audio/a.wav"), recording("/audio/b.wav")])
        sources = SourceList().add_folder(gathered).remove(SourceKey.recording(Path("/audio/a.wav")))

        assert sources.row_count == 1
        assert sources.paths == (Path("/audio/b.wav"),)

    def test_a_folder_left_holding_nothing_goes_along_with_its_last_recording(self) -> None:
        gathered = folder("/audio", [recording("/audio/a.wav")])
        sources = SourceList().add_folder(gathered).remove(SourceKey.recording(Path("/audio/a.wav")))
        assert sources.rows == ()

    def test_a_recording_the_reader_named_goes_on_its_own(self) -> None:
        sources = SourceList().add_recording(recording("/audio/a.wav")).add_recording(recording("/audio/b.wav"))
        sources = sources.remove(SourceKey.recording(Path("/audio/a.wav")))
        assert sources.paths == (Path("/audio/b.wav"),)


class TestSettlingWhatARowStandsFor(BaseTestSuite):
    def test_a_recording_settles_on_its_own(self) -> None:
        row = recording("/audio/a.wav")
        sources = SourceList().add_recording(row).settled(row.key, CHANNEL_SLOT, ChannelName.NOISE, True)

        settled = sources.recording(Path("/audio/a.wav"))
        assert settled is not None
        assert settled.settings.channel_set == {ChannelName.PULSE1, ChannelName.NOISE}

    def test_a_folder_settles_every_recording_it_holds(self) -> None:
        gathered = folder("/audio", [recording("/audio/a.wav"), recording("/audio/b.wav")])
        sources = SourceList().add_folder(gathered).settled(gathered.key, CHANNEL_SLOT, ChannelName.NOISE, True)

        assert all(ChannelName.NOISE in source.settings.channel_set for source in sources.recordings)

    def test_settling_a_folder_leaves_the_rows_beside_it_alone(self) -> None:
        loose = recording("/other/a.wav")
        gathered = folder("/audio", [recording("/audio/a.wav")])
        sources = SourceList().add_recording(loose).add_folder(gathered)
        sources = sources.settled(gathered.key, CHANNEL_SLOT, ChannelName.NOISE, True)

        untouched = sources.recording(Path("/other/a.wav"))
        assert untouched is not None
        assert untouched.settings.channel_set == {ChannelName.PULSE1}


class TestHowAFolderReads(BaseTestSuite):
    def test_a_folder_every_recording_of_which_holds_it_reads_as_all(self) -> None:
        gathered = folder("/audio", [recording("/audio/a.wav"), recording("/audio/b.wav")])
        sources = SourceList().add_folder(gathered)
        assert sources.agreement(gathered.key, CHANNEL_SLOT, ChannelName.PULSE1) == Agreement.ALL

    def test_a_folder_whose_recordings_differ_reads_as_some(self) -> None:
        gathered = folder(
            "/audio",
            [recording("/audio/a.wav", [ChannelName.PULSE1]), recording("/audio/b.wav", [ChannelName.NOISE])],
        )
        sources = SourceList().add_folder(gathered)
        assert sources.agreement(gathered.key, CHANNEL_SLOT, ChannelName.PULSE1) == Agreement.SOME

    def test_a_folder_no_recording_of_which_holds_it_reads_as_none(self) -> None:
        gathered = folder("/audio", [recording("/audio/a.wav", [ChannelName.PULSE1])])
        sources = SourceList().add_folder(gathered)
        assert sources.agreement(gathered.key, CHANNEL_SLOT, ChannelName.NOISE) == Agreement.NONE

    def test_a_row_the_list_has_none_of_reads_as_none(self) -> None:
        assert (
            SourceList().agreement(SourceKey.recording(Path("/audio/a.wav")), CHANNEL_SLOT, ChannelName.PULSE1)
            == Agreement.NONE
        )


class TestOneGestureOnARow(BaseTestSuite):
    def test_a_folder_its_recordings_disagree_on_settles_on_all_of_them(self) -> None:
        gathered = folder(
            "/audio",
            [recording("/audio/a.wav", [ChannelName.PULSE1]), recording("/audio/b.wav", [ChannelName.NOISE])],
        )
        sources = SourceList().add_folder(gathered).toggled(gathered.key, CHANNEL_SLOT, ChannelName.PULSE1)
        assert sources.agreement(gathered.key, CHANNEL_SLOT, ChannelName.PULSE1) == Agreement.ALL

    def test_a_folder_every_recording_of_which_holds_it_lets_it_go(self) -> None:
        gathered = folder("/audio", [recording("/audio/a.wav"), recording("/audio/b.wav")])
        sources = SourceList().add_folder(gathered).toggled(gathered.key, CHANNEL_SLOT, ChannelName.PULSE1)
        assert sources.agreement(gathered.key, CHANNEL_SLOT, ChannelName.PULSE1) == Agreement.NONE

    def test_a_bend_settles_the_same_way_a_channel_does(self) -> None:
        gathered = folder(
            "/audio",
            [
                recording("/audio/a.wav", [ChannelName.TRIANGLE]),
                recording("/audio/b.wav", [ChannelName.TRIANGLE]),
            ],
        )
        sources = SourceList().add_folder(gathered).toggled(gathered.key, BEND_SLOT, ChannelName.TRIANGLE)
        assert sources.agreement(gathered.key, BEND_SLOT, ChannelName.TRIANGLE) == Agreement.ALL
