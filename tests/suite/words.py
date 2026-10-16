import itertools
from typing import Iterator, Sequence, Tuple, TypeVar

SymbolT = TypeVar("SymbolT")


def words(alphabet: Sequence[SymbolT], *, longest: int) -> Iterator[Tuple[SymbolT, ...]]:
    """Every word over ``alphabet`` up to ``longest`` symbols long, shorter words first, the empty word among them.

    A state machine checked over every such word has met every order its events can come in, up to that
    length, which is what a model check reads as the machine's whole behavior within the bound.
    """
    for length in range(longest + 1):
        yield from itertools.product(alphabet, repeat=length)
