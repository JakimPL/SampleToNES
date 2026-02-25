from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from sampletones.utils.meta import NonInstantiableMeta


@dataclass(frozen=True, kw_only=True)
class BaseTestCase(metaclass=NonInstantiableMeta):
    __test__ = False


@dataclass(frozen=True, kw_only=True)
class BaseRegularTestCase(BaseTestCase, metaclass=NonInstantiableMeta):
    label: str
    expected: Any = None


@dataclass(frozen=True, kw_only=True)
class BaseAutolabelTestCase(BaseTestCase, metaclass=NonInstantiableMeta):
    expected: Any = None

    @property
    @abstractmethod
    def label(self) -> str:
        pass
