from dataclasses import dataclass, replace
from typing import List, Mapping, Optional, Protocol, Self, Sequence, Tuple, Union

import numpy as np

from sampletones_core.constants.enums import GeneratorClassName
from sampletones_core.fft import Fragment
from sampletones_core.reconstructions.reconstructor.candidates import CandidateProvider
from sampletones_core.reconstructions.reconstructor.mix import FrameMix
from sampletones_core.reconstructions.reconstructor.window.surroundings import ChannelSurroundings, NoteKey
from sampletones_shared.array import to_numpy, xp

from .catalog import KindCatalog
from .layout import StemLayout

RowSet = Union[Sequence[int], np.ndarray]


class FrameHearing(Protocol):
    """How one frame of a stem hears the rows its channels may play.

    Every comparison the joint assignment makes adds its channels' rows into the frame's reading.
    A hearing answers what the frame holds before any of its rows sound, and what each row adds when
    a channel plays it, at the drive the stem gives the channel.
    """

    @property
    def leak(self) -> np.ndarray:
        """The power the frame holds before any of its rows sound."""

    @property
    def leak_features(self) -> np.ndarray:
        """The feature values of ``leak``."""

    def powers(self, place: int, rows: RowSet) -> np.ndarray:
        """The power each row adds when the channel at ``place`` in the layout plays it, one row per row."""

    def features(self, place: int, rows: RowSet) -> np.ndarray:
        """The feature values of what each row adds, one row per row."""

    def unit_powers(self, place: int, rows: RowSet) -> np.ndarray:
        """What each row adds as a fit of its level reads it: a scale of the row's power."""

    def unit_features(self, place: int, rows: RowSet) -> np.ndarray:
        """The feature values of ``unit_powers``."""

    def place_of(self, kind: GeneratorClassName, row: int) -> int:
        """The place of the stem's channel of ``kind`` that hears ``row`` the way a proposal of it is read."""

    def empty_mix(self, fragment: Fragment) -> FrameMix:
        """The mix of no rows, holding what the frame holds before its rows sound."""


@dataclass(frozen=True)
class SteadyHearing:
    """A frame heard alone, every row as a note held through the whole analysis window.

    A row adds its library power at the channel's drive, and the frame holds nothing before its
    rows sound. This is how the frames are first assigned, before any neighbor is known.
    """

    layout: StemLayout
    catalogs: Mapping[GeneratorClassName, KindCatalog]
    bins: int

    @property
    def leak(self) -> np.ndarray:
        return np.zeros(self.bins)

    @property
    def leak_features(self) -> np.ndarray:
        return np.zeros(self.bins)

    def powers(self, place: int, rows: RowSet) -> np.ndarray:
        slot = self.layout.slots[place]
        return np.asarray(self.catalogs[slot.kind].powers[list(rows)] / slot.drive**2)

    def features(self, place: int, rows: RowSet) -> np.ndarray:
        slot = self.layout.slots[place]
        return np.asarray(self.catalogs[slot.kind].features[list(rows)] / slot.drive**2)

    def unit_powers(self, place: int, rows: RowSet) -> np.ndarray:
        return self.powers(place, rows)

    def unit_features(self, place: int, rows: RowSet) -> np.ndarray:
        return self.features(place, rows)

    def place_of(self, kind: GeneratorClassName, row: int) -> int:  # pylint: disable=unused-argument
        return _places(self.layout, kind)[0]

    def empty_mix(self, fragment: Fragment) -> FrameMix:
        return FrameMix.empty(fragment)


@dataclass(frozen=True)
class SequenceHearing:
    """A frame heard among the notes its neighbors were decoded to play.

    The analysis window of a frame reads its neighbors too. What they play is a fixed part of the
    frame's reading, and a row the frame plays adds its own share of the window, extending a note
    held up to the frame or from it where it sounds that note.

    Attributes:
        layout: The stem's channels.
        catalogs: Each kind's rows.
        surroundings: What each of the stem's channels holds around the frame, in layout order.
        provider: The candidate provider, which turns powers into feature values.
        leak: The power the stem's channels' other frames leave in the frame.
        leak_features: The feature values of ``leak``.
    """

    layout: StemLayout
    catalogs: Mapping[GeneratorClassName, KindCatalog]
    surroundings: Tuple[ChannelSurroundings, ...]
    provider: CandidateProvider
    leak: np.ndarray
    leak_features: np.ndarray

    @classmethod
    def of(
        cls,
        layout: StemLayout,
        catalogs: Mapping[GeneratorClassName, KindCatalog],
        surroundings: Sequence[ChannelSurroundings],
        provider: CandidateProvider,
    ) -> Self:
        """The hearing of a frame whose channels stand among ``surroundings``, in layout order."""
        leak = np.sum([channel.leak for channel in surroundings], axis=0)
        return cls(
            layout=layout,
            catalogs=catalogs,
            surroundings=tuple(surroundings),
            provider=provider,
            leak=leak,
            leak_features=_features(provider, leak[None, :])[0],
        )

    def powers(self, place: int, rows: RowSet) -> np.ndarray:
        return self.surroundings[place].heard(self._keys(place, rows), self._library_powers(place, rows))

    def features(self, place: int, rows: RowSet) -> np.ndarray:
        return _features(self.provider, self.powers(place, rows))

    def unit_powers(self, place: int, rows: RowSet) -> np.ndarray:
        gains = self.surroundings[place].gains(self._keys(place, rows))
        return np.asarray(gains * self._library_powers(place, rows))

    def unit_features(self, place: int, rows: RowSet) -> np.ndarray:
        return _features(self.provider, self.unit_powers(place, rows))

    def place_of(self, kind: GeneratorClassName, row: int) -> int:
        """The channel of ``kind`` whose held note ``row`` extends, the first of the kind where none does."""
        places = _places(self.layout, kind)
        key = self.catalogs[kind].key(row)
        extending = [place for place in places if self.surroundings[place].extends(key)]
        return (extending or places)[0]

    def empty_mix(self, fragment: Fragment) -> FrameMix:
        return replace(FrameMix.empty(fragment), power=self.leak)

    def _keys(self, place: int, rows: RowSet) -> List[Optional[NoteKey]]:
        catalog = self.catalogs[self.layout.slots[place].kind]
        return [catalog.key(int(row)) for row in rows]

    def _library_powers(self, place: int, rows: RowSet) -> np.ndarray:
        slot = self.layout.slots[place]
        return np.asarray(self.catalogs[slot.kind].powers[list(rows)] / slot.drive**2)


def _places(layout: StemLayout, kind: GeneratorClassName) -> List[int]:
    """The places in the layout of the stem's channels of ``kind``."""
    return [place for place, slot in enumerate(layout.slots) if slot.kind == kind]


def _features(provider: CandidateProvider, powers: np.ndarray) -> np.ndarray:
    """The feature values of a stack of powers."""
    return np.asarray(to_numpy(provider.features_of(xp.asarray(powers))), dtype=np.float64)
