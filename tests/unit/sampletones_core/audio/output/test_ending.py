import pytest

from sampletones_core.audio.output import EndCause, Ending, ReadKind, SourceRead


class TestEnding:
    """An ending carries an error exactly when it is a failure."""

    def test_a_failure_carries_its_error(self) -> None:
        error = RuntimeError("the device failed")

        assert Ending.failure(error) == Ending(cause=EndCause.FAILED, error=error)

    def test_a_failure_without_its_error_is_refused(self) -> None:
        with pytest.raises(ValueError):
            Ending(cause=EndCause.FAILED, error=None)

    def test_a_stop_with_an_error_is_refused(self) -> None:
        with pytest.raises(ValueError):
            Ending(cause=EndCause.STOPPED, error=RuntimeError("the device failed"))


class TestSourceRead:
    """A read carries an error exactly when the source failed it."""

    def test_a_failed_read_carries_its_error(self) -> None:
        error = RuntimeError("the source failed")

        assert SourceRead.failed(error).kind is ReadKind.FAILED

    def test_a_last_read_with_an_error_is_refused(self) -> None:
        with pytest.raises(ValueError):
            SourceRead(kind=ReadKind.LAST, error=RuntimeError("the source failed"))
