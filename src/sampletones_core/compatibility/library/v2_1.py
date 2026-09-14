from typing import Final, FrozenSet

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
from sampletones_shared.types.array import ArrayOrNumeric
from sampletones_shared.types.data import SerializedData

SOURCE_DATA_VERSION: Final[str] = "2.0"
TARGET_DATA_VERSION: Final[str] = "2.1"

WINDOWED_METHODS: Final[FrozenSet[str]] = frozenset({"fft", "logfft"})
PHASES_PER_SAMPLE: Final[int] = 100
SPECTRUM_FLOOR: Final[float] = (1 / 15) ** 2
GAMMA_RANGE: Final[int] = 100
STORED_DTYPE: Final = np.float32


def _transformed(density: ArrayOrNumeric, gamma: int) -> ArrayOrNumeric:
    """The 2.0 feature transform of a power density: Yeo-Johnson at `λ = 1 - γ`, the log at `γ = 1`."""
    transformed: ArrayOrNumeric
    if gamma == GAMMA_RANGE:
        transformed = np.log1p(density / SPECTRUM_FLOOR)
    else:
        exponent = 1.0 - gamma / GAMMA_RANGE
        transformed = (np.power(density + SPECTRUM_FLOOR, exponent) - SPECTRUM_FLOOR**exponent) / exponent

    return transformed


def _untransformed(feature: ArrayOrNumeric, gamma: int) -> ArrayOrNumeric:
    """The power density a 2.0 feature value stands for, the inverse of :func:`_transformed`."""
    density: ArrayOrNumeric
    if gamma == GAMMA_RANGE:
        density = SPECTRUM_FLOOR * np.expm1(feature)
    else:
        exponent = 1.0 - gamma / GAMMA_RANGE
        density = np.power(exponent * feature + SPECTRUM_FLOOR**exponent, 1.0 / exponent) - SPECTRUM_FLOOR

    return density


def _repaired_values(
    values: bytes,
    edges: bytes,
    gamma: int,
) -> bytes:
    """The values of one feature restated as the transformed mean of the spectra it was averaged from.

    A 2.0 feature holds `f(ΣS) / f(N)` per unit of bin width: the transformed sum of the phase
    spectra over the transformed phase count. Multiplying by `f(N)` and inverting the transform
    recovers the sum, and the mean follows from it in closed form.
    """
    widths = np.diff(np.frombuffer(edges, dtype=STORED_DTYPE).astype(np.float64))
    densities = np.frombuffer(values, dtype=STORED_DTYPE).astype(np.float64) / widths
    total = _untransformed(densities * _transformed(float(PHASES_PER_SAMPLE), gamma), gamma)
    mean = np.asarray(_transformed(total / PHASES_PER_SAMPLE, gamma))
    return (mean * widths).astype(STORED_DTYPE).tobytes()


def _repaired_item(
    item: SerializedData,
    gamma: int,
) -> SerializedData:
    fragment = item[FRAGMENT]
    feature = fragment[FEATURE]
    values = _repaired_values(feature[VALUES], feature[EDGES], gamma)
    return {**item, FRAGMENT: {**fragment, FEATURE: {**feature, VALUES: values}}}


def update(data: SerializedData) -> SerializedData:
    """Restates every feature of a windowed library as the transformed mean of its phase spectra.

    Data version 2.0 stored `f(ΣS) / f(N)` for a candidate's phase spectra `S`, which is their mean
    only while the transform is the identity: the constant-Q method, and every method at gamma
    zero, stand as they are. Data version 2.1 transforms the mean spectrum. The step holds its own
    copy of the 2.0 transform and its constants, so it reads a 2.0 file the same whatever the
    transform later becomes.
    """
    config = data[CONFIG]
    gamma = config[TRANSFORMATION_GAMMA]
    if config[SPECTRUM_METHOD] not in WINDOWED_METHODS or gamma == 0:
        return data

    return {**data, ITEMS: [_repaired_item(item, gamma) for item in data[ITEMS]]}


V2_1: Final[VersionUpdate] = VersionUpdate(
    kind=ObjectKind.LIBRARY,
    base=Version.model_validate(SOURCE_DATA_VERSION),
    target=Version.model_validate(TARGET_DATA_VERSION),
    apply=update,
)
