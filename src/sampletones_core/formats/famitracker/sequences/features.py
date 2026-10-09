from typing import Dict, Final, Optional

from sampletones_core.constants.enums import FeatureKey
from sampletones_core.exporters.feature import Features
from sampletones_core.exporters.truncation import (
    EnvelopeTruncation,
    instrument_truncation,
)
from sampletones_core.features.envelope import Envelope
from sampletones_core.features.limits import within_limit
from sampletones_core.formats.famitracker.model.sequence import InstrumentSequence
from sampletones_core.formats.famitracker.specification.sequences import (
    BEND_SEQUENCE_KINDS,
    FEATURE_KEY_TO_SEQUENCE_KIND,
    LOOP_FROM_START,
    MAX_SEQUENCE_ITEMS,
    NO_LOOP_POINT,
    SequenceKind,
)

NO_ARPEGGIO_STEP: Final[int] = 0
NO_BEND_STEP: Final[int] = 0
FLAT_RUNNING_ARPEGGIO: Final[Envelope[int]] = Envelope[int](items=(NO_ARPEGGIO_STEP,), loop_point=LOOP_FROM_START)


def features_to_instrument_sequences(
    features: Features,
    *,
    repitched: bool,
) -> Dict[SequenceKind, InstrumentSequence]:
    """Builds the five 2A03 sequences from a channel slice's envelopes.

    Each dimension becomes an :class:`InstrumentSequence`; one the generator lacks, or one left
    to the channel, becomes a disabled sequence the instrument stores nothing for. Every dimension
    keeps the length it was written at and the item it repeats from, which is how FamiTracker
    advances each sequence on a counter of its own, and each stands within the items the file
    holds — see :func:`stored_envelope`.

    A bend travels with an arpeggio that runs beside it, which is what makes the bend an offset
    from the note — see :func:`_pinned`. An instrument a note slide reaches keeps its arpeggio and
    its bend running for as long as the note sounds — see :func:`_running`.

    Args:
        features: The per-dimension envelopes describing the slice.
        repitched: Whether a transpose row's note slide reaches the instrument in a module.

    Returns:
        Dict[SequenceKind, InstrumentSequence]: The sequences, one per dimension FamiTracker holds.
    """
    stored = _pinned(_stored_envelopes(features))
    if repitched:
        stored = _running(stored)

    return {kind: _sequence(kind, stored.get(kind, Envelope[int]())) for kind in SequenceKind}


def stored_envelope(
    feature_key: FeatureKey,
    envelope: Envelope[int],
) -> Envelope[int]:
    """One dimension as a FamiTracker file holds it, within the items a sequence stores.

    The item limit belongs to the file, and :func:`within_limit` is the rule every format shortens
    a dimension by.

    Args:
        feature_key: The dimension being written.
        envelope: The dimension as the instrument carries it.

    Returns:
        Envelope[int]: The dimension within the items the file holds.
    """
    return within_limit(feature_key, envelope, MAX_SEQUENCE_ITEMS)


def stored_length(feature_key: FeatureKey, envelope: Envelope[int]) -> int:
    """The items a FamiTracker file holds of one dimension.

    A reader watching an envelope grow and an export reporting what it wrote read this one answer,
    so the length a file holds is decided in one place.

    Args:
        feature_key: The dimension being written.
        envelope: The dimension as the instrument carries it.

    Returns:
        int: The items its sequence stores.
    """
    return len(stored_envelope(feature_key, envelope).items)


def features_truncation(features: Features) -> Optional[EnvelopeTruncation]:
    """What a FamiTracker file leaves out of one instrument's envelopes.

    Args:
        features: The per-dimension envelopes describing the instrument.

    Returns:
        Optional[EnvelopeTruncation]: The shortening the file imposes, and ``None`` where every
            dimension is held whole.
    """
    return instrument_truncation(features, stored_length)


def _pinned(stored: Dict[SequenceKind, Envelope[int]]) -> Dict[SequenceKind, Envelope[int]]:
    """These sequences with an arpeggio that runs for as long as the bend beside it acts.

    FamiTracker walks an instrument's sequences in slot order, and an arpeggio in absolute mode
    reloads the period from the note before the bend sequences add to it. So while the arpeggio
    runs, a bend item is the offset from the note that this project writes it as; once the
    arpeggio halts, the same items start accumulating on the running period instead. Writing an
    arpeggio that covers the bend is what holds the two readings together.

    A bend that repeats, or ends on an offset it then holds, acts for as long as the note sounds,
    so the arpeggio and the bend both run on (see :func:`_running`). A bend ending with no offset
    acts until its last item, which an arpeggio reaching its length covers.

    Args:
        stored: The sequences as the file holds them.

    Returns:
        Dict[SequenceKind, Envelope[int]]: Those sequences, the arpeggio covering the bend.
    """
    bends = [bend for kind in BEND_SEQUENCE_KINDS if (bend := stored.get(kind, Envelope[int]())).items]
    if not bends:
        return stored

    if any(_acts_throughout(bend) for bend in bends):
        return _running(stored)

    bend_length = max(len(bend.items) for bend in bends)
    return {**stored, SequenceKind.ARPEGGIO: _pinning_arpeggio(stored, bend_length)}


def _acts_throughout(bend: Envelope[int]) -> bool:
    """Whether a bend offsets the note for as long as it sounds: it repeats, or it holds an offset when it ends."""
    return bend.loops or bend.items[-1] != NO_BEND_STEP


def _pinning_arpeggio(stored: Dict[SequenceKind, Envelope[int]], bend_length: int) -> Envelope[int]:
    """The arpeggio that reloads the note for every tick a bend ending with no offset states one for.

    An arpeggio circling from a point runs for as long as the note sounds and needs nothing; one
    playing its items once holds its final note over the remaining ticks, which is the note it
    would rest on anyway; and an instrument writing no arpeggio at all takes one item at its own
    note, repeating.

    Args:
        stored: The sequences as the file holds them.
        bend_length: The ticks the longest bend dimension states.

    Returns:
        Envelope[int]: The arpeggio to write.
    """
    arpeggio = stored.get(SequenceKind.ARPEGGIO, Envelope[int]())
    if arpeggio.loops:
        return arpeggio

    if not arpeggio.items:
        return FLAT_RUNNING_ARPEGGIO

    return arpeggio.resized(max(len(arpeggio.items), bend_length))


def _running(stored: Dict[SequenceKind, Envelope[int]]) -> Dict[SequenceKind, Envelope[int]]:
    """These sequences with the arpeggio and the bend circling on their last item, so each runs as long as the note.

    A note slide moves the channel's note, and an arpeggio in absolute mode reloads the period from the
    note every tick it runs, so the moved note sounds from the slide's own tick. A halted arpeggio
    reloads nothing and the slide's glide is heard instead, so the arpeggio circles on its last item,
    which is the note it rests on anyway, and an instrument writing none takes one item at its own
    note. The bend is added to the period the arpeggio reloads, and a halted bend adds nothing, so a
    bend circles on its last item too and holds the offset it ends on.

    Args:
        stored: The sequences as the file holds them, the arpeggio already covering the bend.

    Returns:
        Dict[SequenceKind, Envelope[int]]: Those sequences, the arpeggio and the bend running.
    """
    arpeggio = stored.get(SequenceKind.ARPEGGIO, Envelope[int]())
    running = {
        **stored,
        SequenceKind.ARPEGGIO: _circling(arpeggio) if arpeggio.items else FLAT_RUNNING_ARPEGGIO,
    }
    for kind in BEND_SEQUENCE_KINDS:
        bend = stored.get(kind, Envelope[int]())
        if bend.items:
            running[kind] = _circling(bend)

    return running


def _circling(envelope: Envelope[int]) -> Envelope[int]:
    """The envelope repeating from its own point, or from its last item where it plays once and holds it."""
    if envelope.loops:
        return envelope

    return Envelope[int](items=envelope.items, loop_point=len(envelope.items) - 1)


def _stored_envelopes(features: Features) -> Dict[SequenceKind, Envelope[int]]:
    """Each dimension the slice offers, as the file holds it."""
    return {
        FEATURE_KEY_TO_SEQUENCE_KIND[feature_key]: stored_envelope(feature_key, envelope)
        for feature_key, envelope in features.envelopes.items()
    }


def _sequence(
    kind: SequenceKind,
    envelope: Envelope[int],
) -> InstrumentSequence:
    """One sequence as the file states it, with the item the dimension repeats from."""
    return InstrumentSequence(
        kind=kind,
        items=envelope.items,
        loop_point=envelope.loop_point if envelope.loop_point is not None else NO_LOOP_POINT,
    )
