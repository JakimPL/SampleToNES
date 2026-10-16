from dataclasses import dataclass
from typing import Tuple

import pytest

from sampletones_core.audio.output import EndCause
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseAutolabelTestCase
from tests.unit.sampletones_core.audio.output.storm import ROUNDS, Storm, broken_rules, causes, describe


class TestStorm(BaseTestSuite):
    """Owners act on one output at once, at random, over a device that is slow and fails now and then, and every
    rule of the output contract holds through it. A broken rule names the seed, what each owner did and what the
    device was asked; the seed repeats what the owners do, and the machine decides the order they meet in."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        expected: None = None
        seed: int

        @property
        def label(self) -> str:
            return f"seed-{self.seed}"

    test_cases: Tuple[TestCase, ...] = (
        TestCase(seed=1),
        TestCase(seed=2),
        TestCase(seed=3),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_every_rule_holds_through_the_storm(self, test_case: TestCase) -> None:
        storm = Storm(test_case.seed)

        storm.run()

        events = storm.system.timeline.events()
        broken = broken_rules(storm.record, storm.system, storm.output)
        assert not broken, describe(storm.record, events, broken)
        assert len(storm.record.checkpoints) == ROUNDS
        assert causes(storm.record) == set(EndCause), describe(storm.record, events, ["some ending never came"])
