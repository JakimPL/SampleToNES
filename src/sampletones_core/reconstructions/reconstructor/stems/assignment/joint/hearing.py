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
from .layout import Slot, StemLayout

RowSet = Union[Sequence[int], np.ndarray]


class FrameHearing(Protocol):
    """How one frame of a stem hears the rows its channels may play.

    Every comparison the joint assignment makes adds its channels' rows into the frame's reading.
    A hearing answers what the frame holds before any of its rows sound, its leak, and what each
    row adds when a channel plays it, at the drive the stem gives the channel. The joint assignment
    adds feature values as it adds powers, which holds where the features read power linearly, at a
    transformation gamma of zero.
    """

    @property
    def leak(self) -> np.ndarray:
        """The power the frame holds before any of its rows sound."""

    @property
    def leak_features(self) -> np.ndarray:
        """The feature values of ``leak``."""

    def powers(self, place: int, rows: RowSet) -> np.ndarray:
        """The power each of ``rows`` adds when the channel at ``place`` in the layout plays it, one row per row."""

    def features(self, place: int, rows: RowSet) -> np.ndarray:
        """The feature values of what each of ``rows`` adds, one row per row."""

    def unit_powers(self, place: int, rows: RowSet) -> np.ndarray:
        """What each of ``rows`` adds as a fit of its level reads it: a scale of the row's power."""

    def unit_features(self, place: int, rows: RowSet) -> np.ndarray:
        """The feature values of ``unit_powers``."""

    def place_of(self, kind: GeneratorClassName, row: int) -> int:
        """The place of the channel of ``kind`` a proposal of ``row`` is heard on, before a choice places it."""

    def empty_mix(self, fragment: Fragment) -> FrameMix:
        """The mix of no rows, holding what the frame holds before its rows sound."""


@dataclass(frozen=True)
class SteadyHearing:
    """A frame heard alone, every row as a note held through the whole analysis window.

    This is how the frames are first assigned, before any neighbor is known. A note held through
    the whole window reaches the frame whole, so a row adds its library power at the channel's
    drive, and a fit reads it at that power. The frame holds nothing before its rows sound.

    Attributes:
        layout: The stem's channels.
        catalogs: Each kind's rows.
        bins: How many bins the frame's feature holds.
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
        return _library_powers(self.layout, self.catalogs, place, rows)

    def features(self, place: int, rows: RowSet) -> np.ndarray:
        """Each row's library feature values at the channel's drive, scaled as its power is.

        These are the feature values of the row's power at the drive where the features read power
        linearly, at a transformation gamma of zero.
        """
        slot = self.layout.slots[place]
        return _at_drive(self.catalogs[slot.kind].features, rows, slot)

    def unit_powers(self, place: int, rows: RowSet) -> np.ndarray:
        return self.powers(place, rows)

    def unit_features(self, place: int, rows: RowSet) -> np.ndarray:
        return self.features(place, rows)

    def place_of(self, kind: GeneratorClassName, row: int) -> int:  # pylint: disable=unused-argument
        """The first channel of ``kind``: a frame heard alone joins no held note, so it hears every row there."""
        return _places(self.layout, kind)[0]

    def empty_mix(self, fragment: Fragment) -> FrameMix:
        return FrameMix.empty(fragment)


@dataclass(frozen=True)
class SequenceHearing:
    """A frame heard among the notes its neighbors were decoded to play.

    The analysis window of a frame reads its neighbors too. What they play stays fixed while the
    frame is decided, so the power they leave is the frame's leak, which every mix holds before any
    row sounds. The channels add in power, so the stem's leak is the sum of its channels' leaks.

    A row adds what its channel's surroundings hear of its library power at the channel's drive:
    its own share of the window, joined with the note held up to the frame or from it where the row
    sounds that note. A fit reads a row through the surroundings' gain.

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
        """The hearing of a frame whose channels stand among ``surroundings``, in layout order.

        ``surroundings`` must hold at least one channel.
        """
        leak = np.sum([channel.leak for channel in surroundings], axis=0)
        return cls(
            layout=layout,
            catalogs=catalogs,
            surroundings=tuple(surroundings),
            provider=provider,
            leak=leak,
            leak_features=cls._features(provider, leak[None, :])[0],
        )

    def powers(self, place: int, rows: RowSet) -> np.ndarray:
        library_powers = _library_powers(self.layout, self.catalogs, place, rows)
        return self.surroundings[place].heard(self._keys(place, rows), library_powers)

    def features(self, place: int, rows: RowSet) -> np.ndarray:
        return self._features(self.provider, self.powers(place, rows))

    def unit_powers(self, place: int, rows: RowSet) -> np.ndarray:
        gains = self.surroundings[place].gains(self._keys(place, rows))
        return np.asarray(gains * _library_powers(self.layout, self.catalogs, place, rows))

    def unit_features(self, place: int, rows: RowSet) -> np.ndarray:
        return self._features(self.provider, self.unit_powers(place, rows))

    def place_of(self, kind: GeneratorClassName, row: int) -> int:
        """The channel of ``kind`` whose held note ``row`` extends, the first of the kind where none does.

        A row extending a channel's held note reaches the frame joined with it on that channel
        alone. Where several channels hold the note, the first of them hears it.
        """
        places = _places(self.layout, kind)
        key = self.catalogs[kind].key(row)
        extending = [place for place in places if self.surroundings[place].extends(key)]
        return (extending or places)[0]

    def empty_mix(self, fragment: Fragment) -> FrameMix:
        """The mix of no rows, its power the leak.

        The leak is what the analysis window reads of the other frames. The frame's own samples
        sound none of it, so the mix's expected waveform and variance stay those of silence.
        """
        return replace(FrameMix.empty(fragment), power=self.leak)

    def _keys(self, place: int, rows: RowSet) -> List[Optional[NoteKey]]:
        """The note and timbre each of ``rows`` sounds on the channel at ``place``, ``None`` for silence."""
        catalog = self.catalogs[self.layout.slots[place].kind]
        return [catalog.key(int(row)) for row in rows]

    @staticmethod
    def _features(provider: CandidateProvider, powers: np.ndarray) -> np.ndarray:
        """The feature values of a stack of powers, as host arrays in double precision.

        The provider transforms powers on the active array backend, and the joint assignment reads
        every feature value as a NumPy array of doubles.
        """
        return np.asarray(to_numpy(provider.features_of(xp.asarray(powers))), dtype=np.float64)


def _library_powers(
    layout: StemLayout, catalogs: Mapping[GeneratorClassName, KindCatalog], place: int, rows: RowSet
) -> np.ndarray:
    """Each row's library power at the drive of the channel at ``place``, as a note held through the window."""
    slot = layout.slots[place]
    return _at_drive(catalogs[slot.kind].powers, rows, slot)


def _at_drive(values: np.ndarray, rows: RowSet, slot: Slot) -> np.ndarray:
    """The library values of ``rows``, one per row and read at unit drive, as the channel of ``slot`` reads them.

    A drive ``d`` asks the channel to play its part of the stem's audio ``d`` times louder. The stem's
    audio is one target for all its channels, each at its own drive, so the rows are scaled instead:
    each is read at ``1 / d`` of its library amplitude, its power divided by ``d²``, and the row
    matching the audio is the one ``d`` times louder.
    """
    return np.asarray(values[list(rows)] / slot.drive**2)


def _places(layout: StemLayout, kind: GeneratorClassName) -> List[int]:
    """The places in the layout of the stem's channels of ``kind``, in channel order."""
    return [place for place, slot in enumerate(layout.slots) if slot.kind == kind]
