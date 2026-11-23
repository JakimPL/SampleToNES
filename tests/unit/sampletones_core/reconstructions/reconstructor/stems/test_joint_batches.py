import numpy as np

from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.batches import cheapest_row, split_by_group
from tests.suite.base import BaseTestSuite


class TestABatchOfGroups(BaseTestSuite):
    """Groups of rows scored in one batch read their own costs back, group after group."""

    def test_each_group_reads_the_stretch_of_costs_its_rows_were_stacked_in(self) -> None:
        groups = [np.array([7, 8]), np.array([3]), np.array([5, 6, 9])]

        stretches = split_by_group(np.arange(6.0), groups)

        assert [stretch.tolist() for stretch in stretches] == [[0.0, 1.0], [2.0], [3.0, 4.0, 5.0]]

    def test_an_empty_group_reads_no_costs(self) -> None:
        groups = [np.array([1]), np.array([], dtype=np.int64), np.array([2])]

        stretches = split_by_group(np.array([0.5, 0.25]), groups)

        assert [stretch.tolist() for stretch in stretches] == [[0.5], [], [0.25]]

    def test_the_cheapest_row_is_the_one_at_the_lowest_cost(self) -> None:
        assert cheapest_row(np.array([4, 9, 2]), np.array([0.3, 0.1, 0.2])) == 9

    def test_of_equally_cheap_rows_the_earlier_stands(self) -> None:
        assert cheapest_row(np.array([4, 9, 2]), np.array([0.3, 0.1, 0.1])) == 9
