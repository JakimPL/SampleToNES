from dataclasses import dataclass
from typing import Callable, Generic, Sequence, TypeVar

ContextT = TypeVar("ContextT")


@dataclass(frozen=True, kw_only=True)
class ScenarioStep(Generic[ContextT]):
    """A single named step in a test scenario.

    The action receives the shared (mutable) scenario context and performs both
    the operation under test and its assertions. Steps are ordered, so a step
    observes every mutation made by the steps before it.
    """

    __test__ = False

    label: str
    action: Callable[[ContextT], None]


@dataclass(frozen=True, kw_only=True)
class BaseTestScenario(Generic[ContextT]):
    """An ordered sequence of steps sharing one mutable context.

    Unlike a :class:`BaseTestCase`, which describes a single input/output pair, a
    scenario models a stateful sequence of operations: ``build`` produces the
    initial context, then :meth:`run` threads it through each step in turn. This
    fits behaviours that only emerge over a sequence of mutations -- reordering a
    collection, editing an item in place, and asserting that references survive.
    """

    __test__ = False

    label: str
    build: Callable[[], ContextT]
    steps: Sequence[ScenarioStep[ContextT]]

    def run(self) -> ContextT:
        context = self.build()
        for step in self.steps:
            step.action(context)

        return context
