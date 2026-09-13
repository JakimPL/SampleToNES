import pytest

from bootstrap.interpreter import DOWNLOADS, require_python


class TestRequirePython:
    def test_an_interpreter_at_least_the_version_passes(self, capsys: pytest.CaptureFixture[str]) -> None:
        require_python((3, 8))

        assert "Detected Python version" in capsys.readouterr().out

    def test_an_older_interpreter_is_refused_with_the_download_site(self) -> None:
        with pytest.raises(SystemExit) as refused:
            require_python((99, 0))

        assert DOWNLOADS in str(refused.value)
