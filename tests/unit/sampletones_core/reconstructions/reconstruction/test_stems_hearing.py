from typing import Final, FrozenSet, List, Tuple

import numpy as np

from sampletones_core.audio.mixing import align
from sampletones_core.constants.algorithm import AUTHORED_STEM_ID, RESTING_STEM_ID
from sampletones_core.constants.enums import ChannelName, bending_channels
from sampletones_core.reconstructions.reconstruction.renders import rendered_channels, rendered_mix
from sampletones_core.reconstructions.reconstruction.stems.channel_assignment import ChannelAssignment
from sampletones_core.reconstructions.reconstruction.stems.data import StemsData
from sampletones_core.reconstructions.reconstruction.stems.hearing import Hearing, heard_renders
from sampletones_core.reconstructions.reconstruction.stems.selection import StemSelection
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from tests.suite.stems import RECORDED_SCALE, SHARED_CHANNEL, SOLE_CHANNEL, STEM_A_ID, STEM_B_ID, taking_turns

__all__ = ["taking_turns"]

EVERY_CHANNEL: Final[FrozenSet[ChannelName]] = frozenset(ChannelName.items())
CHANNEL: Final[ChannelName] = ChannelName.PULSE1


def _stems_data(*stem_lists: Tuple[ChannelName, List[int]]) -> StemsData:
    entries = [
        StemEntry(
            id=stem_id,
            settings=StemSettings(channels=[CHANNEL], bends=bending_channels([CHANNEL])),
        )
        for stem_id in range(3)
    ]
    return StemsData(
        config=StemsConfig(
            entries=entries,
            hierarchy=StemsHierarchy(levels=[[entry.id] for entry in entries]),
        ),
        assignments=[ChannelAssignment(channel_name=channel, stem_ids=stem_ids) for channel, stem_ids in stem_lists],
        scale=RECORDED_SCALE,
    )


def _hearing(stem_ids: FrozenSet[int], channels_on: FrozenSet[ChannelName] = EVERY_CHANNEL) -> Hearing:
    return Hearing(selection=StemSelection.everywhere(stem_ids, ChannelName.items()), channels_on=channels_on)


class TestWhatAChannelIsFilteredBy:
    """A channel's filter names the owners heard, so two hearings reaching the channel alike read it alike."""

    def test_every_owner_heard_is_heard_whole(self) -> None:
        stems_data = _stems_data((CHANNEL, [0, 1, RESTING_STEM_ID]))

        assert _hearing(frozenset({0, 1})).filter_for(CHANNEL, stems_data) is None

    def test_an_owner_left_out_names_the_owners_heard(self) -> None:
        stems_data = _stems_data((CHANNEL, [0, 1]))

        assert _hearing(frozenset({0})).filter_for(CHANNEL, stems_data) == frozenset({0})

    def test_recordings_beyond_the_channel_are_left_out_of_the_name(self) -> None:
        stems_data = _stems_data((CHANNEL, [0, 1]))

        assert _hearing(frozenset({0, 2})).filter_for(CHANNEL, stems_data) == frozenset({0})
        assert _hearing(frozenset({0, 1, 2})).filter_for(CHANNEL, stems_data) is None

    def test_the_readers_own_row_counts_as_an_owner(self) -> None:
        stems_data = _stems_data((CHANNEL, [0, AUTHORED_STEM_ID]))

        assert _hearing(frozenset({0})).filter_for(CHANNEL, stems_data) == frozenset({0})
        assert _hearing(frozenset({0, AUTHORED_STEM_ID})).filter_for(CHANNEL, stems_data) is None

    def test_a_channel_the_record_leaves_out_is_heard_whole(self) -> None:
        stems_data = _stems_data((CHANNEL, [0]))

        assert _hearing(frozenset()).filter_for(ChannelName.NOISE, stems_data) is None


class TestWhatAHearingSounds:
    """The heard mix and what plays, read from the channels' renders: the arrays handed in come back by
    identity where nothing is filtered, and a narrower choice is summed in channel order.
    """

    def test_heard_whole_and_every_channel_on_sounds_the_mix_itself(self, taking_turns) -> None:
        channels = rendered_channels(taking_turns)
        mixed = rendered_mix(taking_turns)

        heard = heard_renders(taking_turns, _hearing(taking_turns.recorded_stem_ids), channels, mixed)

        assert heard.mix is mixed
        assert heard.playing is mixed

    def test_a_recording_left_out_is_silenced_in_the_mix(self, taking_turns) -> None:
        channels = rendered_channels(taking_turns)
        mixed = rendered_mix(taking_turns)

        heard = heard_renders(taking_turns, _hearing(frozenset({STEM_A_ID})), channels, mixed)

        assert heard.mix is not mixed
        assert np.any(heard.mix != mixed)
        assert heard.playing is heard.mix

    def test_a_channel_switched_off_plays_the_rest(self, taking_turns) -> None:
        channels = rendered_channels(taking_turns)
        mixed = rendered_mix(taking_turns)

        heard = heard_renders(
            taking_turns,
            _hearing(taking_turns.recorded_stem_ids, frozenset({SOLE_CHANNEL})),
            channels,
            mixed,
        )

        assert heard.mix is mixed
        np.testing.assert_array_equal(heard.playing, align([channels[SOLE_CHANNEL]], len(mixed))[0])
        assert len(heard.playing) == len(mixed)

    def test_every_channel_switched_off_plays_silence(self, taking_turns) -> None:
        channels = rendered_channels(taking_turns)
        mixed = rendered_mix(taking_turns)

        heard = heard_renders(taking_turns, _hearing(taking_turns.recorded_stem_ids, frozenset()), channels, mixed)

        np.testing.assert_array_equal(heard.playing, np.zeros_like(mixed))
        assert len(heard.playing) == len(mixed)

    def test_channels_switched_off_beyond_play_change_nothing(self, taking_turns) -> None:
        channels = rendered_channels(taking_turns)
        mixed = rendered_mix(taking_turns)
        on = frozenset({SHARED_CHANNEL, SOLE_CHANNEL, ChannelName.NOISE})

        heard = heard_renders(taking_turns, _hearing(taking_turns.recorded_stem_ids, on), channels, mixed)

        assert heard.playing is mixed
        assert STEM_B_ID in taking_turns.recorded_stem_ids
