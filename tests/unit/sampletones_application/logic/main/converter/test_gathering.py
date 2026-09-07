from pathlib import Path
from typing import FrozenSet, List

from sampletones_application.constants.conversion import MAX_STEM_SOURCES
from sampletones_application.logic.main.converter.gathering import Gathering
from sampletones_application.logic.main.sources.key import SourceKey
from sampletones_application.logic.main.sources.slots import CHANNEL_SLOT
from sampletones_core.constants.enums import ChannelName
from tests.unit.sampletones_application.logic.main.sources.factories import folder, recording


def _mixed(*names: str) -> Gathering:
    """A setup a mix converts: the recordings gathered, and the order they pick in."""
    gathering = Gathering.empty()
    for name in names:
        gathering = gathering.mixing(recording(f"/audio/{name}.wav"))

    return gathering


def _listed(*names: str) -> Gathering:
    """A setup a per-recording run converts: the recordings gathered, no order among them."""
    gathering = Gathering.empty()
    for name in names:
        gathering = gathering.listing(recording(f"/audio/{name}.wav"))

    return gathering


def _names(gathering: Gathering) -> List[str]:
    return [path.stem for path in gathering.paths]


def _mixed_names(gathering: Gathering) -> List[str]:
    return [path.stem for path in gathering.levels.paths]


class TestGatheringRecordings:
    def test_a_recording_stands_in_the_list_and_on_a_level(self) -> None:
        gathering = _mixed("bass")

        assert _names(gathering) == ["bass"]
        assert gathering.recording(Path("/audio/bass.wav")) is not None

    def test_recordings_pick_in_the_order_they_were_mixed(self) -> None:
        assert _names(_mixed("bass", "lead")) == ["bass", "lead"]

    def test_a_recording_already_gathered_keeps_what_it_holds(self) -> None:
        gathering = _mixed("bass").written(
            Path("/audio/bass.wav"),
            CHANNEL_SLOT,
            frozenset({ChannelName.NOISE}),
        )

        gathering = gathering.mixing(recording("/audio/bass.wav", [ChannelName.PULSE1]))

        settled = gathering.recording(Path("/audio/bass.wav"))
        assert settled is not None
        assert settled.settings.channel_set == {ChannelName.NOISE}

    def test_a_recording_leaves_both_sides_of_the_setup(self) -> None:
        gathering = _mixed("bass", "lead").remove(SourceKey.recording(Path("/audio/bass.wav")))

        assert _names(gathering) == ["lead"]
        assert _mixed_names(gathering) == ["lead"]
        assert gathering.recording(Path("/audio/bass.wav")) is None


class TestTheCeilingAMixHoldsTo:
    """A mix reaches as many recordings as the assignment has room to mix, whatever gathers them."""

    def test_an_empty_setup_has_room_for_the_whole_ceiling(self) -> None:
        assert Gathering.empty().room == MAX_STEM_SOURCES

    def test_a_recording_arriving_at_a_full_setup_reaches_neither_side(self) -> None:
        gathering = _mixed(*[f"source{index}" for index in range(MAX_STEM_SOURCES)])

        gathering = gathering.mixing(recording("/audio/one_more.wav"))

        assert gathering.count == MAX_STEM_SOURCES
        assert gathering.recording(Path("/audio/one_more.wav")) is None


class TestSettlingOneRecording:
    def test_a_slot_settles_on_the_recording_named(self) -> None:
        gathering = _mixed("bass", "lead").written(
            Path("/audio/bass.wav"),
            CHANNEL_SLOT,
            frozenset({ChannelName.NOISE}),
        )

        settled = gathering.recording(Path("/audio/bass.wav"))
        untouched = gathering.recording(Path("/audio/lead.wav"))
        assert settled is not None and untouched is not None
        assert settled.settings.channel_set == {ChannelName.NOISE}
        assert untouched.settings.channel_set == {ChannelName.PULSE1}

    def test_settling_a_recording_the_setup_never_gathered_changes_nothing(self) -> None:
        gathering = _mixed("bass")

        assert gathering.written(Path("/audio/stranger.wav"), CHANNEL_SLOT, frozenset()) == gathering


class TestTheListAPerRecordingRunConverts:
    """A run writing one reconstruction apiece converts whatever the list holds, unbounded."""

    def test_a_recording_joins_the_list_without_joining_a_mix(self) -> None:
        gathering = _listed("bass")

        assert _names(gathering) == ["bass"]
        assert _mixed_names(gathering) == []

    def test_the_list_takes_more_than_a_mix_could_hold(self) -> None:
        gathering = _listed(*[f"source{index}" for index in range(MAX_STEM_SOURCES + 3)])

        assert gathering.count == MAX_STEM_SOURCES + 3

    def test_a_folder_stands_for_the_recordings_below_it(self) -> None:
        gathering = Gathering.empty().listing_folder(
            folder("/audio", [recording("/audio/a.wav"), recording("/audio/b.wav")])
        )

        assert gathering.count == 2
        assert gathering.row_count == 1
        assert gathering.folder_root_of(Path("/audio/a.wav")) == Path("/audio")

    def test_a_folder_goes_with_everything_it_stands_for(self) -> None:
        gathering = Gathering.empty().listing_folder(folder("/audio", [recording("/audio/a.wav")]))

        gathering = gathering.remove(SourceKey.folder(Path("/audio")))

        assert gathering.count == 0


class TestTurningToAMix:
    """A mix converts loose recordings and holds a fixed number of them."""

    def test_the_recordings_picked_stand_alone_and_in_order(self) -> None:
        held = folder("/audio", [recording("/audio/a.wav"), recording("/audio/b.wav")])
        gathering = Gathering.empty().listing_folder(held)

        gathering = gathering.mixing_only((recording("/audio/b.wav"),))

        assert _names(gathering) == ["b"]
        assert _mixed_names(gathering) == ["b"]
        assert gathering.folder_root_of(Path("/audio/b.wav")) is None

    def test_a_recording_keeps_the_settings_it_is_named_with(self) -> None:
        gathering = Gathering.empty().listing(recording("/audio/a.wav"))

        named = recording("/audio/a.wav", [ChannelName.NOISE])
        settled = gathering.mixing_only((named,)).recording(Path("/audio/a.wav"))

        assert settled is not None
        assert settled.settings.channel_set == {ChannelName.NOISE}

    def test_a_recording_the_list_never_gathered_joins_it(self) -> None:
        """The mix and the list are one thing, so naming a recording is what brings it in."""
        gathering = _listed("a").mixing_only((recording("/audio/a.wav"), recording("/audio/stranger.wav")))

        assert _names(gathering) == ["a", "stranger"]
        assert _mixed_names(gathering) == ["a", "stranger"]


class TestTurningAwayFromAMix:
    def test_the_list_stands_and_the_picking_order_goes(self) -> None:
        gathering = _mixed("bass", "lead").unmixed()

        assert _names(gathering) == ["bass", "lead"]
        assert _mixed_names(gathering) == []
