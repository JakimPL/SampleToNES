from typing import Sequence, Type

from sampletones_shared.meta import NonInstantiableMeta
from tests.suite.case import BaseTestCase


class BaseTestSuite(metaclass=NonInstantiableMeta):
    TestCase: Type[BaseTestCase]

    test_cases: Sequence[BaseTestCase]
