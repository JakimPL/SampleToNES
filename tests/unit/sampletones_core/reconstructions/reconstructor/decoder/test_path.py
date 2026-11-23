from sampletones_core.reconstructions.reconstructor.decoder.path import traced_back


class TestTracingAPathBack:
    """A path ends on the cheapest last state and follows each state's cheapest predecessor back to the first frame."""

    def test_a_single_frame_is_its_cheapest_state(self) -> None:
        assert traced_back([], [0.3, 0.1, 0.2]) == [1]

    def test_the_path_follows_the_predecessors_back_from_the_cheapest_last_state(self) -> None:
        """The last frame's second state is the cheapest; it came from the first state, which came from the second."""
        backpointers = [[1, 0], [1, 0]]

        assert traced_back(backpointers, [0.5, 0.2]) == [1, 0, 1]

    def test_of_equally_cheap_last_states_the_earliest_ends_the_path(self) -> None:
        assert traced_back([[0, 0, 0]], [0.2, 0.1, 0.1]) == [0, 1]
