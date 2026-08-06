from pathlib import Path
from unittest.mock import MagicMock, patch

from sampletones_application.utils.file_dialogs.backends.command import run_dialog_command

MODULE = "sampletones_application.utils.file_dialogs.backends.command"

COMMAND = ["kdialog", "--getopenfilename"]


def _completed(stdout: str) -> MagicMock:
    result = MagicMock()
    result.stdout = stdout
    return result


class TestRunDialogCommand:
    def test_the_reported_path_reaches_the_caller(self) -> None:
        with patch(f"{MODULE}.subprocess.run", return_value=_completed("/home/user/song.stp\n")) as run:
            result = run_dialog_command(COMMAND)

        assert result == Path("/home/user/song.stp")
        assert run.call_args.args[0] == COMMAND

    def test_the_tool_answers_on_standard_output(self) -> None:
        """The path is read from the captured output, and a dismissal is read from it as well,
        so the exit status stays with the caller of the tool.
        """
        with patch(f"{MODULE}.subprocess.run", return_value=_completed("/audio/clip.wav")) as run:
            run_dialog_command(COMMAND)

        assert run.call_args.kwargs == {"capture_output": True, "text": True, "check": False}

    def test_surrounding_whitespace_leaves_the_path(self) -> None:
        with patch(f"{MODULE}.subprocess.run", return_value=_completed("  /audio/clip.wav \n")):
            assert run_dialog_command(COMMAND) == Path("/audio/clip.wav")

    def test_empty_output_answers_none(self) -> None:
        with patch(f"{MODULE}.subprocess.run", return_value=_completed("\n")):
            assert run_dialog_command(COMMAND) is None
