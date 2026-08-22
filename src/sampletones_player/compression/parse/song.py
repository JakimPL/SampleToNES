from typing import FrozenSet, List, Sequence, Tuple

from sampletones_player.compression.dictionary.phrase import Phrase
from sampletones_player.compression.dictionary.table import PhraseTable
from sampletones_player.compression.matches.cache import MatchCache
from sampletones_player.compression.matches.matcher import PhraseMatcher
from sampletones_player.compression.options import CodecOptions
from sampletones_player.compression.parse.plane import parse_plane
from sampletones_player.compression.parse.result import Parse
from sampletones_player.compression.progress.monitor import CodecMonitor


def parse_planes(
    cache: MatchCache,
    table: PhraseTable,
    options: CodecOptions,
    boundaries: FrozenSet[int],
    monitor: CodecMonitor,
) -> Tuple[Parse, ...]:
    """Reads every plane of a song against one dictionary.

    A plane is where the run looks up: reading one is the longest stretch the codec spends
    without a natural pause, so the monitor hears from it eight times over.

    Args:
        cache: The planes the song covers, alongside what each phrase plays against them.
        table: The phrases the planes may play.
        options: Which of the codec's layers the encoding is built from.
        boundaries: The ticks a token starts on.
        monitor: Carries the run's reckoning of itself onward.

    Returns:
        Tuple[Parse, ...]: One parse per plane, in the order the planes were given.

    Raises:
        OperationCancelled: If the run is no longer wanted.
    """
    parses: List[Parse] = []
    for plane in range(len(cache.indices)):
        parses.append(parse_plane(PhraseMatcher(table, plane, cache), options, boundaries))
        monitor.poll()

    return tuple(parses)


def parse_planes_offered(
    cache: MatchCache,
    table: PhraseTable,
    options: CodecOptions,
    boundaries: FrozenSet[int],
    monitor: CodecMonitor,
    *,
    parses: Sequence[Parse],
    offered: Phrase,
) -> Tuple[Parse, ...]:
    """Reads again the planes ``offered`` reaches, carrying every other parse forward.

    A phrase the plane never plays leaves that plane's tokens exactly as they were: an entry
    appended to the table takes an id after every phrase already in it, so the ids the plane's
    own tokens name are unchanged and the cheapest path across it is the one already found.
    This is what lets the search weigh a candidate for the cost of the planes it touches.

    Args:
        cache: The planes the song covers, alongside what each phrase plays against them.
        table: The phrases the planes may play, ``offered`` among them.
        options: Which of the codec's layers the encoding is built from.
        boundaries: The ticks a token starts on.
        monitor: Carries the run's reckoning of itself onward.
        parses: The parse each plane reached under the table before ``offered`` joined it.
        offered: The phrase the table gained.

    Returns:
        Tuple[Parse, ...]: One parse per plane, in the order the planes were given.

    Raises:
        OperationCancelled: If the run is no longer wanted.
    """
    trial: List[Parse] = []
    for plane in range(len(cache.indices)):
        if not cache.reading(plane, offered).reaches(transposition=options.transposition):
            trial.append(parses[plane])
            continue

        trial.append(parse_plane(PhraseMatcher(table, plane, cache), options, boundaries))
        monitor.poll()

    return tuple(trial)
