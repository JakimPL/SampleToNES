from sampletones_player.compression.matches.index import PlaneIndex


class TestAPlaneIsReadAsStepsAndRuns:
    """Matching is decided against the steps between values and how far each value carries."""

    def test_the_steps_read_the_plane_pairwise(self) -> None:
        assert PlaneIndex.from_plane(bytes((3, 5, 2))).differences == bytes((2, 253))

    def test_a_run_counts_the_ticks_its_value_holds_for(self) -> None:
        assert PlaneIndex.from_plane(bytes((7, 7, 7, 9))).runs == (3, 2, 1, 1)

    def test_a_single_tick_carries_no_steps(self) -> None:
        index = PlaneIndex.from_plane(bytes((5,)))
        assert index.differences == b""
        assert index.ticks == 1
