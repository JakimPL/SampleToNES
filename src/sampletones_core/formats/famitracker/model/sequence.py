from typing import Tuple

from pydantic import BaseModel, ConfigDict, computed_field, field_validator

from sampletones_core.formats.famitracker.specification.sequences import (
    DEFAULT_SEQUENCE_SETTING,
    MAX_SEQUENCE_ITEMS,
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

    @field_validator("items")
    @classmethod
    def _fits_famitracker_sequence(
        cls,
        items: Tuple[int, ...],
    ) -> Tuple[int, ...]:
        """Keeps an instance within the item count FamiTracker can represent.

        FamiTracker holds a sequence in a fixed 252-entry array and stores the count in a
        single byte, and both the ``.ftm`` and ``.fti`` readers write every item they are
        told to read straight into that array. A longer sequence therefore corrupts the
        reader's memory, so the limit belongs to the model rather than to either writer.
        The export path shortens an envelope to this length beforehand, leaving this check
        to hold the invariant for every other construction site.

        Raises:
            ValueError: If the sequence holds more than ``MAX_SEQUENCE_ITEMS`` items.
        """
        if len(items) > MAX_SEQUENCE_ITEMS:
            raise ValueError(
                f"Sequence of {len(items)} items exceeds the FamiTracker limit of {MAX_SEQUENCE_ITEMS} items"
            )
        return items

    @computed_field  # type: ignore[prop-decorator]
    @property
    def enabled(self) -> bool:
        return len(self.items) > 0
