from typing import Final, List, Tuple

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.algorithm import AUTHORED_STEM_ID, RESTING_STEM_ID
from sampletones_core.constants.enums import ChannelName, bending_channels
from sampletones_core.generators.render import render_instructions
from sampletones_core.instructions import InstructionUnion
from sampletones_core.reconstructions.reconstruction.stems.channel_assignment import ChannelAssignment
from sampletones_core.reconstructions.reconstruction.stems.data import StemsData
from sampletones_core.reconstructions.reconstruction.stems.filter import (
    filter_approximations,
)
from sampletones_core.reconstructions.reconstruction.stems.selection import StemSelection
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from tests.suite.long_documents import turning_instruction
from tests.suite.stems import RECORDED_SCALE

FRAME_LENGTH: Final[int] = 2
SOUNDING_FRAME: Final[int] = 0
RESTING_FRAME: Final[int] = 1
FRAMES_AROUND_A_REST: Final[int] = 3
EVERY_CHANNEL: Final[Tuple[ChannelName, ...]] = tuple(ChannelName.items())


def _heard(*stem_ids: int) -> StemSelection:
    """The selection hearing every named stem on every channel."""
    return StemSelection.everywhere(frozenset(stem_ids), EVERY_CHANNEL)


def _stems_data(*stem_lists: Tuple[ChannelName, List[int]]) -> StemsData:
    entries = [
        StemEntry(
            id=stem_id,
            settings=StemSettings(channels=[ChannelName.PULSE1], bends=bending_channels([ChannelName.PULSE1])),
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


class TestFilterApproximations:
    def test_unselected_frames_become_silence(self) -> None:
        stems_data = _stems_data((ChannelName.PULSE1, [0, 1, 0, 2]))
        approximations = {
            ChannelName.PULSE1: np.arange(8, dtype=np.float32),
        }

        filtered = filter_approximations(
            stems_data,
            approximations,
            _heard(0, 2),
            FRAME_LENGTH,
        )

        expected = np.array([0, 1, 0, 0, 4, 5, 6, 7], dtype=np.float32)
        np.testing.assert_array_equal(filtered[ChannelName.PULSE1], expected)
        assert len(filtered[ChannelName.PULSE1]) == len(approximations[ChannelName.PULSE1])

    def test_every_selected_stem_answers_the_original_arrays(self) -> None:
        stems_data = _stems_data((ChannelName.PULSE1, [0, 1, 2]))
        approximations = {
            ChannelName.PULSE1: np.arange(6, dtype=np.float32),
        }

        filtered = filter_approximations(
            stems_data,
            approximations,
            _heard(0, 1, 2),
            FRAME_LENGTH,
        )

        np.testing.assert_array_equal(filtered[ChannelName.PULSE1], approximations[ChannelName.PULSE1])

    def test_no_selected_stem_is_silence(self) -> None:
        stems_data = _stems_data((ChannelName.PULSE1, [0, 1]))
        approximations = {
            ChannelName.PULSE1: np.ones(4, dtype=np.float32),
        }

        filtered = filter_approximations(
            stems_data,
            approximations,
            _heard(),
            FRAME_LENGTH,
        )

        np.testing.assert_array_equal(filtered[ChannelName.PULSE1], np.zeros(4, dtype=np.float32))

    def test_the_stored_arrays_keep_their_samples(self) -> None:
        stems_data = _stems_data((ChannelName.PULSE1, [0, 1]))
        approximations = {
            ChannelName.PULSE1: np.ones(4, dtype=np.float32),
        }

        filter_approximations(
            stems_data,
            approximations,
            _heard(0),
            FRAME_LENGTH,
        )

        np.testing.assert_array_equal(approximations[ChannelName.PULSE1], np.ones(4, dtype=np.float32))

    def test_channels_the_stems_data_names_come_back_filtered(self) -> None:
        stems_data = _stems_data(
            (ChannelName.PULSE1, [0]),
            (ChannelName.NOISE, [1]),
        )
        approximations = {
            ChannelName.PULSE1: np.ones(2, dtype=np.float32),
            ChannelName.NOISE: np.ones(2, dtype=np.float32),
        }

        filtered = filter_approximations(
            stems_data,
            approximations,
            _heard(1),
            FRAME_LENGTH,
        )

        assert set(filtered) == {ChannelName.PULSE1, ChannelName.NOISE}
        np.testing.assert_array_equal(filtered[ChannelName.PULSE1], np.zeros(2, dtype=np.float32))
        np.testing.assert_array_equal(filtered[ChannelName.NOISE], np.ones(2, dtype=np.float32))

    def test_a_stem_heard_on_one_channel_stays_quiet_on_the_other(self) -> None:
        stems_data = _stems_data(
            (ChannelName.PULSE1, [0]),
            (ChannelName.NOISE, [0]),
        )
        approximations = {
            ChannelName.PULSE1: np.ones(2, dtype=np.float32),
            ChannelName.NOISE: np.ones(2, dtype=np.float32),
        }

        filtered = filter_approximations(
            stems_data,
            approximations,
            StemSelection(channels={ChannelName.PULSE1: frozenset({0}), ChannelName.NOISE: frozenset()}),
            FRAME_LENGTH,
        )

        np.testing.assert_array_equal(filtered[ChannelName.PULSE1], np.ones(2, dtype=np.float32))
        np.testing.assert_array_equal(filtered[ChannelName.NOISE], np.zeros(2, dtype=np.float32))


class TestAChannelHeardWhole:
    """A channel every owner of which is heard keeps its array, which a reader tells by identity.

    A resting frame belongs to nobody, so hearing every recording and the reader's own row is
    hearing the channel whole; the frames a mask would zero are silent already, since every
    generator renders a silent instruction as silence.
    """

    def test_every_owner_heard_hands_the_array_back_by_identity(self) -> None:
        stems_data = _stems_data((ChannelName.PULSE1, [0, 1, 0]))
        approximations = {ChannelName.PULSE1: np.arange(6, dtype=np.float32)}

        filtered = filter_approximations(stems_data, approximations, _heard(0, 1), FRAME_LENGTH)

        assert filtered[ChannelName.PULSE1] is approximations[ChannelName.PULSE1]

    def test_resting_frames_leave_the_identity_standing(self) -> None:
        stems_data = _stems_data((ChannelName.PULSE1, [0, RESTING_STEM_ID, 0]))
        approximations = {ChannelName.PULSE1: np.arange(6, dtype=np.float32)}

        filtered = filter_approximations(stems_data, approximations, _heard(0), FRAME_LENGTH)

        assert filtered[ChannelName.PULSE1] is approximations[ChannelName.PULSE1]

    def test_recordings_heard_beyond_the_channel_change_nothing(self) -> None:
        stems_data = _stems_data((ChannelName.PULSE1, [0, 0]))
        approximations = {ChannelName.PULSE1: np.arange(4, dtype=np.float32)}

        filtered = filter_approximations(stems_data, approximations, _heard(0, 1, 2), FRAME_LENGTH)

        assert filtered[ChannelName.PULSE1] is approximations[ChannelName.PULSE1]

    def test_the_readers_own_frames_left_out_are_silenced(self) -> None:
        """The reader's own row answers to boxes like any recording, so leaving it out filters the channel."""
        stems_data = _stems_data((ChannelName.PULSE1, [0, AUTHORED_STEM_ID]))
        approximations = {ChannelName.PULSE1: np.ones(4, dtype=np.float32)}

        filtered = filter_approximations(stems_data, approximations, _heard(0), FRAME_LENGTH)

        assert filtered[ChannelName.PULSE1] is not approximations[ChannelName.PULSE1]
        np.testing.assert_array_equal(filtered[ChannelName.PULSE1], np.array([1, 1, 0, 0], dtype=np.float32))

    def test_an_owner_left_out_hands_back_a_copy(self) -> None:
        stems_data = _stems_data((ChannelName.PULSE1, [0, 1]))
        approximations = {ChannelName.PULSE1: np.ones(4, dtype=np.float32)}

        filtered = filter_approximations(stems_data, approximations, _heard(0), FRAME_LENGTH)

        assert filtered[ChannelName.PULSE1] is not approximations[ChannelName.PULSE1]

    @pytest.mark.parametrize("channel_name", EVERY_CHANNEL, ids=lambda channel_name: channel_name.value)
    def test_a_resting_frame_renders_as_silence(self, channel_name: ChannelName) -> None:
        """What the identity rests on: a silent instruction between two sounding ones renders as exact zeros."""
        config = Config()
        sounding = turning_instruction(channel_name, SOUNDING_FRAME)
        stream: List[InstructionUnion] = [sounding, type(sounding).null_instruction(), sounding]

        rendered = render_instructions(stream, channel_name, config)

        frame_length = config.frame_length
        assert len(rendered) == FRAMES_AROUND_A_REST * frame_length
        resting = rendered[RESTING_FRAME * frame_length : (RESTING_FRAME + 1) * frame_length]
        np.testing.assert_array_equal(resting, np.zeros(frame_length, dtype=np.float32))
