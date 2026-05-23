from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple, Type, Union
from unittest.mock import MagicMock

import pytest

from sampletones_shared.utils.callbacks import CallbackMixin
from tests.sampletones.errors import expect_error
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase


class TestableCallbackClass(CallbackMixin):
    __test__ = False

    def __init__(self) -> None:
        self.on_event: Optional[Any] = None
        self.on_data: Optional[Any] = None
        self.on_error: Optional[Any] = None


def assert_callbacks_match(instance: TestableCallbackClass, expected: Dict[str, Optional[Any]]) -> None:
    for attr_name in ["on_event", "on_data", "on_error"]:
        actual_callback = getattr(instance, attr_name)
        expected_callback = expected[attr_name]

        if expected_callback is None:
            assert actual_callback is None
        elif callable(expected_callback) and callable(actual_callback):
            assert actual_callback() == expected_callback()
        else:
            assert actual_callback == expected_callback


class TestCall(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Union[Any, Type[Exception]]
        callback: Optional[Any]
        args: Tuple[Any, ...]
        kwargs: Dict[str, Any]

    test_cases = [
        TestCase(
            callback=lambda: 42,
            args=(),
            kwargs={},
            expected=42,
            label="lambda_no_args_returns_int",
        ),
        TestCase(
            callback=lambda x: x * 2,
            args=(5,),
            kwargs={},
            expected=10,
            label="lambda_with_positional_arg",
        ),
        TestCase(
            callback=lambda x, y: x + y,
            args=(3, 4),
            kwargs={},
            expected=7,
            label="lambda_with_multiple_positional_args",
        ),
        TestCase(
            callback=lambda x=0: x * 3,
            args=(),
            kwargs={"x": 10},
            expected=30,
            label="lambda_with_keyword_arg",
        ),
        TestCase(
            callback=lambda a, b=1, c=2: a + b + c,
            args=(5,),
            kwargs={"c": 10},
            expected=16,
            label="lambda_with_mixed_args_and_kwargs",
        ),
        TestCase(
            callback=lambda: None,
            args=(),
            kwargs={},
            expected=None,
            label="lambda_returns_none",
        ),
        TestCase(
            callback=lambda: "result",
            args=(),
            kwargs={},
            expected="result",
            label="lambda_returns_string",
        ),
        TestCase(
            callback=lambda: [1, 2, 3],
            args=(),
            kwargs={},
            expected=[1, 2, 3],
            label="lambda_returns_list",
        ),
        TestCase(
            callback=lambda: {"key": "value"},
            args=(),
            kwargs={},
            expected={"key": "value"},
            label="lambda_returns_dict",
        ),
        TestCase(
            callback=None,
            args=(),
            kwargs={},
            expected=None,
            label="none_callback_returns_none",
        ),
        TestCase(
            callback=None,
            args=(1, 2, 3),
            kwargs={"a": 1},
            expected=None,
            label="none_callback_with_args_returns_none",
        ),
        TestCase(
            callback=42,
            args=(),
            kwargs={},
            expected=TypeError,
            label="non_callable_int",
        ),
        TestCase(
            callback="not_callable",
            args=(),
            kwargs={},
            expected=TypeError,
            label="non_callable_string",
        ),
        TestCase(
            callback=[1, 2, 3],
            args=(),
            kwargs={},
            expected=TypeError,
            label="non_callable_list",
        ),
        TestCase(
            callback={"key": "value"},
            args=(),
            kwargs={},
            expected=TypeError,
            label="non_callable_dict",
        ),
        TestCase(
            callback=object(),
            args=(),
            kwargs={},
            expected=TypeError,
            label="non_callable_object",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_call(self, test_case: TestCase) -> None:
        instance = TestableCallbackClass()

        if expect_error(instance.call, test_case.expected, test_case.callback, *test_case.args, **test_case.kwargs):
            return

        result = instance.call(test_case.callback, *test_case.args, **test_case.kwargs)
        assert result == test_case.expected

    def test_call_logs_warning_for_none_callback(self, caplog: pytest.LogCaptureFixture) -> None:
        instance = TestableCallbackClass()
        instance.call(None)
        assert "No callback for TestableCallbackClass to call" in caplog.text

    def test_call_with_callback_that_raises_exception(self) -> None:
        instance = TestableCallbackClass()

        def raising_callback() -> None:
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            instance.call(raising_callback)

    def test_call_with_mock_callback(self) -> None:
        instance = TestableCallbackClass()
        mock_callback = MagicMock(return_value="mocked")

        result = instance.call(mock_callback, 1, 2, key="value")

        assert result == "mocked"
        mock_callback.assert_called_once_with(1, 2, key="value")


class TestSetCallbacks(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Union[Dict[str, Optional[Any]], Type[Exception]]
        initial_callbacks: Dict[str, Optional[Any]]
        set_kwargs: Dict[str, Optional[Any]]

    test_cases = [
        TestCase(
            initial_callbacks={"on_event": None, "on_data": None, "on_error": None},
            set_kwargs={"on_event": lambda: 1},
            expected={"on_event": lambda: 1, "on_data": None, "on_error": None},
            label="set_single_callback",
        ),
        TestCase(
            initial_callbacks={"on_event": None, "on_data": None, "on_error": None},
            set_kwargs={"on_event": lambda: 1, "on_data": lambda: 2},
            expected={"on_event": lambda: 1, "on_data": lambda: 2, "on_error": None},
            label="set_multiple_callbacks",
        ),
        TestCase(
            initial_callbacks={"on_event": None, "on_data": None, "on_error": None},
            set_kwargs={"on_event": lambda: 1, "on_data": lambda: 2, "on_error": lambda: 3},
            expected={"on_event": lambda: 1, "on_data": lambda: 2, "on_error": lambda: 3},
            label="set_all_callbacks",
        ),
        TestCase(
            initial_callbacks={"on_event": lambda: "old", "on_data": None, "on_error": None},
            set_kwargs={"on_event": lambda: "new"},
            expected={"on_event": lambda: "new", "on_data": None, "on_error": None},
            label="override_existing_callback",
        ),
        TestCase(
            initial_callbacks={"on_event": None, "on_data": None, "on_error": None},
            set_kwargs={"on_event": None},
            expected={"on_event": None, "on_data": None, "on_error": None},
            label="set_none_does_not_change",
        ),
        TestCase(
            initial_callbacks={"on_event": lambda: "old", "on_data": None, "on_error": None},
            set_kwargs={"on_event": None},
            expected={"on_event": lambda: "old", "on_data": None, "on_error": None},
            label="set_none_preserves_existing",
        ),
        TestCase(
            initial_callbacks={"on_event": None, "on_data": None, "on_error": None},
            set_kwargs={"on_event": 42},
            expected={"on_event": None, "on_data": None, "on_error": None},
            label="non_callable_int_not_set",
        ),
        TestCase(
            initial_callbacks={"on_event": None, "on_data": None, "on_error": None},
            set_kwargs={"on_event": "not_callable"},
            expected={"on_event": None, "on_data": None, "on_error": None},
            label="non_callable_string_not_set",
        ),
        TestCase(
            initial_callbacks={"on_event": None, "on_data": None, "on_error": None},
            set_kwargs={"on_event": [1, 2, 3]},
            expected={"on_event": None, "on_data": None, "on_error": None},
            label="non_callable_list_not_set",
        ),
        TestCase(
            initial_callbacks={"on_event": None, "on_data": None, "on_error": None},
            set_kwargs={"on_event": lambda: 1, "on_data": None, "on_error": 42},
            expected={"on_event": lambda: 1, "on_data": None, "on_error": None},
            label="mixed_valid_none_and_invalid",
        ),
        TestCase(
            initial_callbacks={"on_event": None, "on_data": None, "on_error": None},
            set_kwargs={},
            expected={"on_event": None, "on_data": None, "on_error": None},
            label="empty_kwargs_no_change",
        ),
        TestCase(
            initial_callbacks={"on_event": None, "on_data": None, "on_error": None},
            set_kwargs={"non_existent": lambda: 1},
            expected=AttributeError,
            label="non_existent_attribute_raises",
        ),
        TestCase(
            initial_callbacks={"on_event": None, "on_data": None, "on_error": None},
            set_kwargs={"on_event": lambda: 1, "invalid_attr": lambda: 2},
            expected=AttributeError,
            label="one_valid_one_invalid_raises",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_set_callbacks(self, test_case: TestCase) -> None:
        instance = TestableCallbackClass()
        instance.on_event = test_case.initial_callbacks["on_event"]
        instance.on_data = test_case.initial_callbacks["on_data"]
        instance.on_error = test_case.initial_callbacks["on_error"]

        if expect_error(instance.set_callbacks, test_case.expected, **test_case.set_kwargs):
            return

        assert not isinstance(test_case.expected, type)
        instance.set_callbacks(**test_case.set_kwargs)
        assert_callbacks_match(instance, test_case.expected)

    def test_set_callbacks_with_mock(self) -> None:
        instance = TestableCallbackClass()
        mock_callback = MagicMock()

        instance.set_callbacks(on_event=mock_callback)
        assert instance.on_event is mock_callback
        assert callable(instance.on_event)


class TestResetCallbacks(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Union[Dict[str, Optional[Any]], Type[Exception]]
        initial_callbacks: Dict[str, Optional[Any]]
        reset_names: Tuple[str, ...]

    test_cases = [
        TestCase(
            initial_callbacks={"on_event": lambda: 1, "on_data": lambda: 2, "on_error": lambda: 3},
            reset_names=("on_event",),
            expected={"on_event": None, "on_data": lambda: 2, "on_error": lambda: 3},
            label="reset_single_callback",
        ),
        TestCase(
            initial_callbacks={"on_event": lambda: 1, "on_data": lambda: 2, "on_error": lambda: 3},
            reset_names=("on_event", "on_data"),
            expected={"on_event": None, "on_data": None, "on_error": lambda: 3},
            label="reset_multiple_callbacks",
        ),
        TestCase(
            initial_callbacks={"on_event": lambda: 1, "on_data": lambda: 2, "on_error": lambda: 3},
            reset_names=("on_event", "on_data", "on_error"),
            expected={"on_event": None, "on_data": None, "on_error": None},
            label="reset_all_callbacks",
        ),
        TestCase(
            initial_callbacks={"on_event": None, "on_data": lambda: 2, "on_error": lambda: 3},
            reset_names=("on_event",),
            expected={"on_event": None, "on_data": lambda: 2, "on_error": lambda: 3},
            label="reset_already_none_callback",
        ),
        TestCase(
            initial_callbacks={"on_event": None, "on_data": None, "on_error": None},
            reset_names=("on_event", "on_data", "on_error"),
            expected={"on_event": None, "on_data": None, "on_error": None},
            label="reset_all_none_callbacks",
        ),
        TestCase(
            initial_callbacks={"on_event": lambda: 1, "on_data": lambda: 2, "on_error": lambda: 3},
            reset_names=(),
            expected={"on_event": lambda: 1, "on_data": lambda: 2, "on_error": lambda: 3},
            label="reset_empty_names_no_change",
        ),
        TestCase(
            initial_callbacks={"on_event": lambda: 1, "on_data": lambda: 2, "on_error": lambda: 3},
            reset_names=("on_event", "on_event"),
            expected={"on_event": None, "on_data": lambda: 2, "on_error": lambda: 3},
            label="reset_duplicate_names",
        ),
        TestCase(
            initial_callbacks={"on_event": lambda: 1, "on_data": lambda: 2, "on_error": lambda: 3},
            reset_names=("non_existent",),
            expected=AttributeError,
            label="reset_non_existent_attribute_raises",
        ),
        TestCase(
            initial_callbacks={"on_event": lambda: 1, "on_data": lambda: 2, "on_error": lambda: 3},
            reset_names=("on_event", "invalid_callback"),
            expected=AttributeError,
            label="reset_one_valid_one_invalid_raises",
        ),
        TestCase(
            initial_callbacks={"on_event": lambda: 1, "on_data": lambda: 2, "on_error": lambda: 3},
            reset_names=("invalid1", "invalid2"),
            expected=AttributeError,
            label="reset_multiple_invalid_raises",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_reset_callbacks(self, test_case: TestCase) -> None:
        instance = TestableCallbackClass()
        instance.on_event = test_case.initial_callbacks["on_event"]
        instance.on_data = test_case.initial_callbacks["on_data"]
        instance.on_error = test_case.initial_callbacks["on_error"]

        if expect_error(instance.reset_callbacks, test_case.expected, *test_case.reset_names):
            return

        assert not isinstance(test_case.expected, type)
        instance.reset_callbacks(*test_case.reset_names)
        assert_callbacks_match(instance, test_case.expected)
