from sampletones_player.shell.patterns import load_patterns
from sampletones_player.specification.screen import PATTERNS_SIZE
from tests.suite.base import BaseTestSuite


class TestTheShippedPatterns(BaseTestSuite):
    def test_they_hold_both_pattern_tables(self) -> None:
        assert len(load_patterns()) == PATTERNS_SIZE
