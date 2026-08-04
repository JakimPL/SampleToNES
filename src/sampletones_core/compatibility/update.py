from typing import NamedTuple

from sampletones_core.compatibility.kind import ObjectKind
from sampletones_shared.deployment.version import Version


class VersionUpdate(NamedTuple):
    kind: ObjectKind
    base: Version
    target: Version
