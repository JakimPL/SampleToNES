from typing import Callable, NamedTuple

from sampletones_core.compatibility.kind import ObjectKind
from sampletones_shared.deployment.version import Version
from sampletones_shared.types.data import SerializedData

UpdateFunction = Callable[[SerializedData], SerializedData]


class VersionUpdate(NamedTuple):
    """One step of a format upgrade: the version it reads, the one it writes, and the transform."""

    kind: ObjectKind
    base: Version
    target: Version
    apply: UpdateFunction
