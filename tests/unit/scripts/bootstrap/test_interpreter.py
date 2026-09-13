import subprocess
import sys
from typing import Final

import pytest

from bootstrap.interpreter import DOWNLOADS, REQUIRED_VERSION, require_python, running_version
from sampletones_tools.checks.paths import SCRIPTS_ROOT

OLDER_INTERPRETER: Final[str] = "(3, 10, 0, 'final', 0)"


class TestRequirePython:
    def test_an_interpreter_at_least_the_version_passes(self) -> None:
        require_python((3, 8))

    def test_an_older_interpreter_is_refused_with_the_download_site(self) -> None:
        with pytest.raises(SystemExit) as refused:
            require_python((99, 0))

        assert DOWNLOADS in str(refused.value)

    def test_the_running_version_reads_major_minor_and_micro(self) -> None:
        assert running_version() == ".".join(str(part) for part in sys.version_info[:3])


class TestBootstrapGate:
    def test_importing_a_helper_on_an_older_interpreter_names_the_required_version(self) -> None:
        probe = f"import sys; sys.version_info = {OLDER_INTERPRETER}; import bootstrap.project"

        completed = subprocess.run(
            [sys.executable, "-c", probe],
            cwd=SCRIPTS_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        major, minor = REQUIRED_VERSION
        assert completed.returncode == 1
        assert f"Python {major}.{minor} or newer is required" in completed.stderr
        assert DOWNLOADS in completed.stderr
