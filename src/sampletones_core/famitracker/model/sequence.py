from __future__ import annotations

from typing import Tuple

from pydantic import BaseModel, ConfigDict, computed_field

from sampletones_core.famitracker.specification.sequences import (
    DEFAULT_SEQUENCE_SETTING,
    NO_LOOP_POINT,
    NO_RELEASE_POINT,
    SequenceKind,
)


class InstrumentSequence(BaseModel):
    """One 2A03 instrument sequence: a per-tick envelope for a single dimension.

    ``items`` holds the signed per-tick values. ``loop_point`` and ``release_point``
    are item indices, or -1 to disable. The frozen, tuple-backed shape makes an
    instance hashable, so identical sequences collapse to one entry in the module's
    shared sequence pool.
    """

    model_config = ConfigDict(frozen=True)

    kind: SequenceKind
    items: Tuple[int, ...] = ()
    loop_point: int = NO_LOOP_POINT
    release_point: int = NO_RELEASE_POINT
    setting: int = DEFAULT_SEQUENCE_SETTING

    @computed_field  # type: ignore[prop-decorator]
    @property
    def enabled(self) -> bool:
        return len(self.items) > 0
