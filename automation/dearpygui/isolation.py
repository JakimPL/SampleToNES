import json
import signal
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import (
    Dict,
    Final,
    List,
    Literal,
    Mapping,
    Optional,
    Sequence,
    Union,
)

import pytest

PHASES: Final[Sequence[Literal["setup", "call", "teardown"]]] = (
    "setup",
    "call",
    "teardown",
)

CHILD_ARGUMENTS: Final[Sequence[str]] = (
    "-p",
    "no:cacheprovider",
    "-p",
    "no:cov",
    "-p",
    "no:xdist",
    "-q",
    "--no-header",
)

OUTPUT_TAIL_CHARACTERS: Final[int] = 20_000
OVERRIDE_OPTION: Final[str] = "override_ini"
OVERRIDE_FLAG: Final[str] = "-o"
NODE_SEPARATOR: Final[str] = "::"
XFAIL_MARKER: Final[str] = "xfail"
XFAIL_REASON: Final[str] = "reason"


@dataclass(frozen=True)
class ChildRun:
    """How a child process ended: its exit status, or ``None`` when it ran out of time, and its output."""

    returncode: Optional[int]
    output: str

    @property
    def crashed(self) -> bool:
        """Whether the process ended by a signal or ran out of time."""
        return self.returncode is None or self.returncode < 0

    @property
    def killed_by_signal(self) -> bool:
        """Whether the process ended by a signal, such as a crash."""
        return self.returncode is not None and self.returncode < 0

    @property
    def ending(self) -> str:
        """The way the process ended, in words a failure report can carry."""
        if self.returncode is None:
            return "ran out of time and was stopped"
        if self.returncode < 0:
            return f"was killed by {signal.Signals(-self.returncode).name}"

        return f"exited with status {self.returncode}"


class ReportRecorder:
    """Writes each report the child's run makes to a file, in the form pytest sends between processes.

    A report is written the moment its phase ends, so a process that dies in a later phase still
    leaves the earlier reports behind.
    """

    def __init__(
        self,
        config: pytest.Config,
        path: Path,
    ) -> None:
        self._config = config
        self._path = path

    @pytest.hookimpl
    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        """Appends the report of one finished phase to the file as a line of JSON."""
        data = self._config.hook.pytest_report_to_serializable(config=self._config, report=report)
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(data) + "\n")


def run_isolated(
    item: pytest.Item,
    *,
    environment: Mapping[str, str],
    working_directory: Path,
    report_path: Path,
    timeout: float,
) -> List[pytest.TestReport]:
    """Runs ``item`` in a fresh interpreter and returns its reports, as if it had run here.

    The child is a pytest run of the item's node id alone, under ``environment`` and started in
    ``working_directory``, which is where the application under test finds itself launched. It
    writes its reports to ``report_path``. A phase missing from them, because the child crashed or
    ran out of time, comes back as a failure carrying the child's output, and so does the last phase
    of a child that crashed after reporting all of them.
    """
    child = _run_child(
        item,
        environment=environment,
        working_directory=working_directory,
        timeout=timeout,
    )
    reports = _read_reports(item.config, report_path)
    return _completed(item, reports, child)


def _run_child(
    item: pytest.Item,
    *,
    environment: Mapping[str, str],
    working_directory: Path,
    timeout: float,
) -> ChildRun:
    command = [
        sys.executable,
        "-m",
        "pytest",
        _located_nodeid(item),
        f"--rootdir={item.config.rootpath}",
        *CHILD_ARGUMENTS,
        *_overrides(item.config),
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=working_directory,
            env=dict(environment),
            timeout=timeout,
            capture_output=True,
            text=True,
            check=False,
        )
    except subprocess.TimeoutExpired as expired:
        return ChildRun(
            returncode=None,
            output=_text(expired.stdout) + _text(expired.stderr),
        )

    return ChildRun(
        returncode=completed.returncode,
        output=completed.stdout + completed.stderr,
    )


def _overrides(config: pytest.Config) -> List[str]:
    """The ``-o`` settings the parent run was started with, which the child collects its item under too."""
    stated: Optional[List[str]] = config.getoption(OVERRIDE_OPTION, default=None)
    return [argument for override in stated or [] for argument in (OVERRIDE_FLAG, override)]


def _located_nodeid(item: pytest.Item) -> str:
    """The item's node id with its file named by an absolute path, which a run started anywhere finds."""
    _, separator, name = item.nodeid.partition(NODE_SEPARATOR)
    return f"{item.path}{separator}{name}"


def _read_reports(config: pytest.Config, path: Path) -> Dict[str, pytest.TestReport]:
    if not path.exists():
        return {}

    reports: Dict[str, pytest.TestReport] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        report = config.hook.pytest_report_from_serializable(config=config, data=json.loads(line))
        reports[report.when] = report

    return reports


def _completed(
    item: pytest.Item,
    reports: Dict[str, pytest.TestReport],
    child: ChildRun,
) -> List[pytest.TestReport]:
    completed: List[pytest.TestReport] = []
    for phase in PHASES:
        report = reports.get(phase)
        if report is None:
            report = _missing_report(item, phase, child, failed=not completed or completed[-1].passed)

        completed.append(report)
        if report.failed and phase == "setup":
            break

    if child.crashed and len(reports) == len(PHASES):
        completed[-1] = _missing_report(item, PHASES[-1], child, failed=True)

    return completed


def _missing_report(
    item: pytest.Item,
    phase: Literal["setup", "call", "teardown"],
    child: ChildRun,
    *,
    failed: bool,
) -> pytest.TestReport:
    """The report of a phase the child never wrote, since the process ended first.

    A scenario marked to fail by a known defect, whose process a signal killed, reports that phase as the expected
    failure it names: a crash is a defect the ledger records like any other.
    """
    expected = item.get_closest_marker(XFAIL_MARKER)
    if failed and child.killed_by_signal and expected is not None:
        return pytest.TestReport(
            nodeid=item.nodeid,
            location=item.location,
            keywords={keyword: 1 for keyword in item.keywords},
            outcome="skipped",
            longrepr=None,
            when=phase,
            wasxfail=f"{expected.kwargs.get(XFAIL_REASON, '')} (the process {child.ending})",
        )

    longrepr = None
    if failed:
        longrepr = (
            f"The scenario's process {child.ending} around its {phase}.\n\n{child.output[-OUTPUT_TAIL_CHARACTERS:]}"
        )

    return pytest.TestReport(
        nodeid=item.nodeid,
        location=item.location,
        keywords={keyword: 1 for keyword in item.keywords},
        outcome="failed" if failed else "passed",
        longrepr=longrepr,
        when=phase,
    )


def _text(output: Optional[Union[bytes, str]]) -> str:
    if output is None:
        return ""
    if isinstance(output, bytes):
        return output.decode(errors="replace")

    return output
