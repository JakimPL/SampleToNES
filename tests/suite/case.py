from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from sampletones_shared.meta import NonInstantiableMeta


@dataclass(frozen=True, kw_only=True)
class BaseTestCase(metaclass=NonInstantiableMeta):
    __test__ = False


@dataclass(frozen=True, kw_only=True)
class BaseRegularTestCase(BaseTestCase, metaclass=NonInstantiableMeta):
    label: str
    expected: Any


@dataclass(frozen=True, kw_only=True)
class BaseAutolabelTestCase(BaseTestCase, metaclass=NonInstantiableMeta):
    expected: Any

    @property
    @abstractmethod
    def label(self) -> str:
        pass
