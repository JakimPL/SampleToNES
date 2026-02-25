from functools import wraps
from typing import Callable, TypeVar

import pytest

from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

TestCaseT = TypeVar("TestCaseT", bound=BaseRegularTestCase)


def parametrized(func: Callable[[BaseTestSuite, TestCaseT], None]) -> Callable[[BaseTestSuite, TestCaseT], None]:
    @wraps(func)
    def wrapper(self: BaseTestSuite, test_case: TestCaseT) -> None:
        parametrized_function: Callable[[BaseTestSuite, TestCaseT], None] = pytest.mark.parametrize(
            "test_case",
            self.test_cases,
            ids=lambda test_case: test_case.label,
            indirect=False,
        )(func)

        return parametrized_function(self, test_case)

    return wrapper
