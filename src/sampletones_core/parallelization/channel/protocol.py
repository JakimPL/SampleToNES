from typing import Optional, Protocol

from sampletones_core.parallelization.task import TaskReport, TaskStep


class StepReporter(Protocol):
    """A task's line back to the run that started it.

    A task says where it stands and hears whether the run still wants its answer, which is the
    contract a run inside one process already reports itself by; what a line adds is the distance
    the report travels. One line serves one task, so a report names the task it came from without
    that task holding an opinion on its own place in the run.
    """

    def __call__(self, step: TaskStep) -> bool:
        """Carries the step, and answers whether the run goes on."""


class ProgressChannel(Protocol):
    """The line a run and the tasks it handed out hold each other on.

    Progress travels one way and a withdrawal the other, so one channel carries both directions of
    the conversation. What a channel is made of follows from where its tasks run, which is why a
    run reaches its tasks through this contract rather than through any one way of crossing to them.
    """

    def reporter(self, index: int) -> StepReporter:
        """The line the task at ``index`` reports on, which travels to wherever that task runs."""

    def poll(self, timeout: float) -> Optional[TaskReport]:
        """The next report a task filed, waiting up to ``timeout`` seconds for one to arrive."""

    def withdraw(self) -> None:
        """Tells every task the run has let go of the answer it was building."""

    def close(self) -> None:
        """Ends the channel and releases whatever it held open for the tasks to reach."""
