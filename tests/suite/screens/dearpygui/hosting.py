import threading
from typing import Callable, Final, List, Protocol

SCENARIO_THREAD_NAME: Final[str] = "scenario"


class ScenarioHangError(AssertionError):
    """Raised when a scenario's thread is still running after the application stopped."""


class HostedLoop(Protocol):
    """An application's render loop, run on the main thread while a scenario drives it from another.

    The host runs the loop where a windowing system wants its events handled. The scenario finishes
    the run from its own thread, and the host closes it once the loop has returned.
    """

    def run(self) -> None:
        """Draws frames on this thread until the application stops."""

    def finish(self, *, failed: bool) -> None:
        """Brings the application to a stop once the scenario is done. Runs on the scenario's thread.

        Raises:
            AssertionError: Naming what the application showed wrong while it stopped.
        """

    def close(self) -> None:
        """Reads what the stopped application left behind. Runs on the main thread after the loop.

        Raises:
            AssertionError: Naming what the application left wrong.
        """


def host(
    scenario: Callable[[], None],
    loop: HostedLoop,
    *,
    join_timeout: float,
) -> None:
    """Runs ``scenario`` on a thread of its own while this thread runs ``loop``, then reports how it went.

    The first failure is the one raised, and every later one rides along as a note on it, so a
    failing scenario still reports what its application did wrong on the way out.

    Raises:
        BaseException: The first failure met: the scenario's own, the finish's or the close's.
        ScenarioHangError: If the scenario's thread outlives the loop by more than ``join_timeout``.
    """
    failures: List[BaseException] = []

    def drive() -> None:
        try:
            scenario()
        except BaseException as error:  # pylint: disable=broad-exception-caught
            failures.append(error)

        try:
            loop.finish(failed=bool(failures))
        except BaseException as error:  # pylint: disable=broad-exception-caught
            failures.append(error)

    thread = threading.Thread(target=drive, name=SCENARIO_THREAD_NAME, daemon=True)
    thread.start()
    loop.run()
    thread.join(join_timeout)
    if thread.is_alive():
        failures.append(
            ScenarioHangError(f"The scenario was still running {join_timeout} s after the application stopped")
        )

    try:
        loop.close()
    except AssertionError as error:
        failures.append(error)

    _raise_first(failures)


def _raise_first(failures: List[BaseException]) -> None:
    if not failures:
        return

    first, *rest = failures
    for later in rest:
        first.add_note(f"Also: {type(later).__name__}: {later}")

    raise first
