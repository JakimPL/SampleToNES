from typing import Final, List, Tuple

import numpy as np

from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions.reconstruction.stems.channel_assignment import ChannelAssignment
from sampletones_core.reconstructions.reconstruction.stems.data import StemsData
from sampletones_core.reconstructions.reconstruction.stems.filter import (
    filter_approximations,
)
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy

FRAME_LENGTH: Final[int] = 2


def _stems_data(*stem_lists: Tuple[ChannelName, List[int]]) -> StemsData:
    entries = [StemEntry(id=stem_id, channels=[ChannelName.PULSE1]) for stem_id in range(3)]
    return StemsData(
        config=StemsConfig(
            entries=entries,
            hierarchy=StemsHierarchy(levels=[[entry.id] for entry in entries]),
        ),
        assignments=[ChannelAssignment(channel_name=channel, stem_ids=stem_ids) for channel, stem_ids in stem_lists],
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
            {0, 2},
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
            {0, 1, 2},
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
            set(),
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
            {0},
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
            {1},
            FRAME_LENGTH,
        )

        assert set(filtered) == {ChannelName.PULSE1, ChannelName.NOISE}
        np.testing.assert_array_equal(filtered[ChannelName.PULSE1], np.zeros(2, dtype=np.float32))
        np.testing.assert_array_equal(filtered[ChannelName.NOISE], np.ones(2, dtype=np.float32))
