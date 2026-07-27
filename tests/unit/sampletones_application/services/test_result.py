from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from sampletones_application.services.result import (
    ServiceCancelled,
    ServiceError,
    ServiceIntermediate,
    ServiceProgress,
    ServiceStarted,
    ServiceSuccess,
)


class TestServiceStarted:
    def test_stores_total(self) -> None:
        started = ServiceStarted(total=10)
        assert started.total == 10

    def test_frozen(self) -> None:
        started = ServiceStarted(total=5)
        with pytest.raises(FrozenInstanceError):
            started.total = 0  # type: ignore[misc]

    def test_equality(self) -> None:
        assert ServiceStarted(total=3) == ServiceStarted(total=3)
        assert ServiceStarted(total=3) != ServiceStarted(total=4)


class TestServiceProgress:
    def test_stores_completed_and_total(self) -> None:
        progress = ServiceProgress(completed=2, total=10)
        assert progress.completed == 2
        assert progress.total == 10

    def test_current_item_defaults_to_none(self) -> None:
        progress = ServiceProgress(completed=1, total=5)
        assert progress.current_item is None

    def test_eta_seconds_defaults_to_none(self) -> None:
        progress = ServiceProgress(completed=1, total=5)
        assert progress.eta_seconds is None

    def test_stores_optional_fields(self) -> None:
        progress = ServiceProgress(
            completed=3,
            total=10,
            current_item=Path("/some/file.wav"),
            eta_seconds=42.5,
        )
        assert progress.current_item == Path("/some/file.wav")
        assert progress.eta_seconds == 42.5

    def test_frozen(self) -> None:
        progress = ServiceProgress(completed=0, total=1)
        with pytest.raises(FrozenInstanceError):
            progress.completed = 1  # type: ignore[misc]

    def test_equality(self) -> None:
        assert ServiceProgress(completed=1, total=5) == ServiceProgress(completed=1, total=5)
        assert ServiceProgress(completed=1, total=5) != ServiceProgress(completed=2, total=5)


class TestServiceSuccess:
    def test_stores_value(self) -> None:
        path = Path("/output/result.nes")
        success = ServiceSuccess(value=path)
        assert success.value == path

    def test_frozen(self) -> None:
        success = ServiceSuccess(value="result")
        with pytest.raises(FrozenInstanceError):
            success.value = "other"  # type: ignore[misc]

    def test_equality(self) -> None:
        assert ServiceSuccess(value=42) == ServiceSuccess(value=42)
        assert ServiceSuccess(value=42) != ServiceSuccess(value=99)


class TestServiceError:
    def test_stores_exception(self) -> None:
        exception = RuntimeError("runtime_error")
        error = ServiceError(exception=exception)
        assert error.exception is exception

    def test_frozen(self) -> None:
        error = ServiceError(exception=RuntimeError())
        with pytest.raises(FrozenInstanceError):
            error.exception = ValueError()  # type: ignore[misc]

    def test_eq_false_same_exception_instances_differ(self) -> None:
        exception = RuntimeError("same")
        error_a = ServiceError(exception=exception)
        error_b = ServiceError(exception=exception)
        # eq=False on the dataclass: identity-based comparison only
        assert error_a != error_b
        assert error_a is not error_b

    def test_same_instance_equals_itself(self) -> None:
        error = ServiceError(exception=RuntimeError())
        assert error == error  # noqa: PLR0124


class TestServiceCancelled:
    def test_instantiates(self) -> None:
        cancelled = ServiceCancelled()
        assert isinstance(cancelled, ServiceCancelled)

    def test_frozen(self) -> None:
        cancelled = ServiceCancelled()
        with pytest.raises(FrozenInstanceError):
            cancelled.x = 1  # type: ignore[attr-defined]

    def test_equality(self) -> None:
        assert ServiceCancelled() == ServiceCancelled()


class TestServiceIntermediate:
    def test_stores_data(self) -> None:
        data = {"key": "value"}
        intermediate = ServiceIntermediate(data=data)
        assert intermediate.data is data

    def test_frozen(self) -> None:
        intermediate = ServiceIntermediate(data=42)
        with pytest.raises(FrozenInstanceError):
            intermediate.data = 0  # type: ignore[misc]

    def test_equality(self) -> None:
        assert ServiceIntermediate(data=1) == ServiceIntermediate(data=1)
        assert ServiceIntermediate(data=1) != ServiceIntermediate(data=2)
