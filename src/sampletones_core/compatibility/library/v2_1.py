from typing import Any, Final, FrozenSet, Optional

import numpy as np

from sampletones_core.compatibility.fields import (
    CONFIG,
    EDGES,
    FEATURE,
    FRAGMENT,
    ITEMS,
    SPECTRUM_METHOD,
    TRANSFORMATION_GAMMA,
    VALUES,
)
from sampletones_core.compatibility.kind import ObjectKind
from sampletones_core.compatibility.update import VersionUpdate
from sampletones_shared.deployment.version import Version
from sampletones_shared.types.data import SerializedData
from sampletones_shared.utils.transformations.morpher import LogMorpher
from sampletones_shared.utils.transformations.transformation import Transformation

SOURCE_DATA_VERSION: Final[str] = "2.0"
TARGET_DATA_VERSION: Final[str] = "2.1"

WINDOWED_METHODS: Final[FrozenSet[str]] = frozenset({"fft", "logfft"})
PHASES_PER_SAMPLE: Final[int] = 100
SPECTRUM_FLOOR: Final[float] = (1 / 15) ** 2
GAMMA_RANGE: Final[int] = 100
STORED_DTYPE: Final = np.float32


def _repaired_values(
    values: bytes,
    edges: bytes,
    transformation: Transformation,
) -> bytes:
    """The values of one feature restated as the transformed mean of the spectra it was averaged from.

    A 2.0 feature holds `f(ΣS) / f(N)` per unit of bin width, the transformed sum of the phase
    spectra divided by the transformed phase count. Multiplying by `f(N)` and inverting the transform
    recovers the sum, and the mean follows from it in closed form.
    """
    widths = np.diff(np.frombuffer(edges, dtype=STORED_DTYPE).astype(np.float64))
    densities = np.frombuffer(values, dtype=STORED_DTYPE).astype(np.float64) / widths
    total = transformation.backward(densities * transformation.forward(float(PHASES_PER_SAMPLE)))
    mean = transformation.forward(total / PHASES_PER_SAMPLE)
    return (mean * widths).astype(STORED_DTYPE).tobytes()


def _repaired_item(item: Any, transformation: Transformation) -> Any:
    if not isinstance(item, dict):
        return item

    fragment = item.get(FRAGMENT)
    if not isinstance(fragment, dict):
        return item

    feature = fragment.get(FEATURE)
    if not isinstance(feature, dict):
        return item

    values = _repaired_values(feature[VALUES], feature[EDGES], transformation)
    return {**item, FRAGMENT: {**fragment, FEATURE: {**feature, VALUES: values}}}


def _averaging_transformation(data: SerializedData) -> Optional[Transformation]:
    """The transform a library averaged its features through, where that average needs restating.

    The windowed methods averaged each candidate's phases in feature space, which is the mean of the
    spectra only while the transform is the identity. The constant-Q method averaged the spectra
    themselves.
    """
    config = data.get(CONFIG)
    if not isinstance(config, dict) or config.get(SPECTRUM_METHOD) not in WINDOWED_METHODS:
        return None

    gamma = config.get(TRANSFORMATION_GAMMA)
    if not isinstance(gamma, int) or gamma == 0:
        return None

    return LogMorpher(gamma=gamma / GAMMA_RANGE, epsilon=SPECTRUM_FLOOR).transformation


def update(data: SerializedData) -> SerializedData:
    """Restates every feature of a windowed library as the transformed mean of its phase spectra.

    Data version 2.0 averaged a candidate's phase features in feature space, summing them through
    the transform and dividing by the transformed count, which holds for the identity alone. Data
    version 2.1 transforms the mean spectrum. The step restates the 2.0 averaging with the values it
    was written with, so it reads a 2.0 file the same whatever those values later become.
    """
    transformation = _averaging_transformation(data)
    items = data.get(ITEMS)
    if transformation is None or not isinstance(items, list):
        return data

    return {**data, ITEMS: [_repaired_item(item, transformation) for item in items]}


V2_1: Final[VersionUpdate] = VersionUpdate(
    kind=ObjectKind.LIBRARY,
    base=Version.model_validate(SOURCE_DATA_VERSION),
    target=Version.model_validate(TARGET_DATA_VERSION),
    apply=update,
)
