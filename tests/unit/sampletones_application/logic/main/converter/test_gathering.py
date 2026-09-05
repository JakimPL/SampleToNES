from pathlib import Path
from typing import FrozenSet, List

from sampletones_application.constants.conversion import MAX_STEM_SOURCES
from sampletones_application.logic.main.converter.gathering import Gathering
from sampletones_application.logic.main.sources.slots import CHANNEL_SLOT
from sampletones_core.constants.enums import ChannelName
from tests.unit.sampletones_application.logic.main.sources.factories import recording


def _gathered(*names: str) -> Gathering:
    gathering = Gathering.empty()
    for name in names:
        gathering = gathering.add(recording(f"/audio/{name}.wav"))

    return gathering


def _names(gathering: Gathering) -> List[str]:
    return [path.stem for path in gathering.paths]


class TestGatheringRecordings:
    def test_a_recording_stands_in_the_list_and_on_a_level(self) -> None:
        gathering = _gathered("bass")

        assert _names(gathering) == ["bass"]
        assert gathering.recording(Path("/audio/bass.wav")) is not None

    def test_recordings_pick_in_the_order_they_were_gathered(self) -> None:
        assert _names(_gathered("bass", "lead")) == ["bass", "lead"]

    def test_a_recording_already_gathered_keeps_what_it_holds(self) -> None:
        gathering = _gathered("bass").written(
            Path("/audio/bass.wav"),
            CHANNEL_SLOT,
            frozenset({ChannelName.NOISE}),
        )

        gathering = gathering.add(recording("/audio/bass.wav", [ChannelName.PULSE1]))

        settled = gathering.recording(Path("/audio/bass.wav"))
        assert settled is not None
        assert settled.settings.channel_set == {ChannelName.NOISE}

    def test_a_recording_leaves_both_sides_of_the_setup(self) -> None:
        gathering = _gathered("bass", "lead").remove(Path("/audio/bass.wav"))

        assert _names(gathering) == ["lead"]
        assert gathering.recording(Path("/audio/bass.wav")) is None


class TestTheCeilingAMixHoldsTo:
    """A mix reaches as many recordings as the assignment has room to mix, whatever gathers them."""

    def test_an_empty_setup_has_room_for_the_whole_ceiling(self) -> None:
        assert Gathering.empty().room == MAX_STEM_SOURCES

    def test_a_recording_arriving_at_a_full_setup_reaches_neither_side(self) -> None:
        gathering = _gathered(*[f"source{index}" for index in range(MAX_STEM_SOURCES)])

        gathering = gathering.add(recording("/audio/one_more.wav"))

        assert gathering.count == MAX_STEM_SOURCES
        assert gathering.recording(Path("/audio/one_more.wav")) is None


class TestSettlingOneRecording:
    def test_a_slot_settles_on_the_recording_named(self) -> None:
        gathering = _gathered("bass", "lead").written(
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
        gathering = _gathered("bass")

        assert gathering.written(Path("/audio/stranger.wav"), CHANNEL_SLOT, frozenset()) == gathering


class TestSettlingAmongTheChannelsOffered:
    """A reader answers for the channels the run enables, and the rest stands as it was."""

    def _held(self, gathering: Gathering) -> FrozenSet[ChannelName]:
        settled = gathering.recording(Path("/audio/bass.wav"))
        assert settled is not None
        return settled.settings.channel_set

    def test_a_channel_left_out_of_the_run_keeps_the_choice_it_was_given(self) -> None:
        gathering = Gathering.empty().add(recording("/audio/bass.wav", [ChannelName.PULSE1, ChannelName.NOISE]))

        gathering = gathering.written_among(
            Path("/audio/bass.wav"),
            CHANNEL_SLOT,
            frozenset(),
            frozenset({ChannelName.PULSE1}),
        )

        assert self._held(gathering) == {ChannelName.NOISE}

    def test_a_channel_the_reader_answered_for_settles_to_the_answer(self) -> None:
        gathering = Gathering.empty().add(recording("/audio/bass.wav", [ChannelName.PULSE1]))

        gathering = gathering.written_among(
            Path("/audio/bass.wav"),
            CHANNEL_SLOT,
            frozenset({ChannelName.PULSE2}),
            frozenset({ChannelName.PULSE1, ChannelName.PULSE2}),
        )

        assert self._held(gathering) == {ChannelName.PULSE2}

    def test_a_recording_the_setup_never_gathered_changes_nothing(self) -> None:
        gathering = _gathered("bass")

        assert gathering.written_among(Path("/audio/stranger.wav"), CHANNEL_SLOT, frozenset(), frozenset()) == gathering


class TestWhatAMixLeavesBehind:
    def test_the_recording_that_picks_first_stays(self) -> None:
        assert _names(_gathered("bass", "lead").kept_first()) == ["bass"]

    def test_the_recordings_it_leaves_go_from_the_list_as_well(self) -> None:
        gathering = _gathered("bass", "lead").kept_first()

        assert gathering.recording(Path("/audio/lead.wav")) is None
        assert gathering.sources.count == 1
