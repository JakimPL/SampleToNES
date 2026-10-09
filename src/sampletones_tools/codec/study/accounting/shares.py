from dataclasses import dataclass
from math import ceil
from typing import Final, List, Sequence

from sampletones_player.specification.compression import (
    MAX_HOLD_TICKS,
    OPCODE_SIZE,
    TokenTag,
)
from sampletones_tools.codec.study.accounting.finding import NOTHING, Finding
from sampletones_tools.codec.study.accounting.tokens import ReadToken

WIDE_HOLD_SIZE: Final[int] = 2
WIDE_HOLD_UNITS: Final[int] = MAX_HOLD_TICKS
BEND_SUFFIX: Final[str] = "_bend"


@dataclass(frozen=True)
class PlaneShares:
    """Where one plane's stream bytes go, token kind by token kind.

    Attributes:
        name: The plane's name in the song block.
        stream: The bytes the stream takes.
        hold_opcodes: The bytes spent on hold opcodes.
        literal_opcodes: The bytes spent on literal opcodes.
        literal_payload: The bytes spent on the values literals carry.
        phrase_bytes: The bytes spent on phrase tokens.
        idle: Whether the plane keeps one value throughout the song.
        bend: Whether the plane is a bend plane.
        hold_chains: What a wide hold would reach (H1): runs of consecutive holds.
    """

    name: str
    stream: int
    hold_opcodes: int
    literal_opcodes: int
    literal_payload: int
    phrase_bytes: int
    idle: bool
    bend: bool
    hold_chains: Finding


def plane_shares(
    name: str,
    plane: bytes,
    tokens: Sequence[ReadToken],
) -> PlaneShares:
    """Accounts for one plane's stream.

    Args:
        name: The plane's name in the song block.
        plane: The values the plane plays.
        tokens: The tokens the plane's stream was read back as.

    Returns:
        PlaneShares: The bytes by token kind, and what a wide hold would reach.
    """
    return PlaneShares(
        name=name,
        stream=sum(token.size for token in tokens),
        hold_opcodes=sum(token.size for token in tokens if token.tag is TokenTag.HOLD),
        literal_opcodes=sum(OPCODE_SIZE for token in tokens if token.tag is TokenTag.LITERAL),
        literal_payload=sum(len(token.payload) for token in tokens),
        phrase_bytes=sum(token.size for token in tokens if token.names_a_phrase),
        idle=len(set(plane)) == 1,
        bend=name.endswith(BEND_SUFFIX),
        hold_chains=hold_chains(tokens),
    )


def hold_chains(tokens: Sequence[ReadToken]) -> Finding:
    """What a wide hold would spare on runs of consecutive holds (H1).

    A hold covers at most ``MAX_HOLD_TICKS``, so a plane resting longer pays an opcode per that
    many ticks. A wide hold on the free escape takes two bytes and counts full holds instead of
    ticks, so a chain is priced as the wide holds its full holds need and one plain hold for
    the ticks left over.

    Args:
        tokens: The tokens of one plane's stream.

    Returns:
        Finding: The hold opcodes in chains, and the bytes wide holds would spare on them.
    """
    finding = NOTHING
    for chain in _chains(tokens):
        full, rest = divmod(sum(token.ticks for token in chain), MAX_HOLD_TICKS)
        if full == 0:
            continue

        now = OPCODE_SIZE * len(chain)
        wide = WIDE_HOLD_SIZE * ceil(full / WIDE_HOLD_UNITS) + (OPCODE_SIZE if rest else 0)
        finding += Finding(now, max(0, now - wide))

    return finding


def _chains(tokens: Sequence[ReadToken]) -> List[List[ReadToken]]:
    chains: List[List[ReadToken]] = []
    current: List[ReadToken] = []
    for token in tokens:
        if token.tag is TokenTag.HOLD:
            current.append(token)
            continue

        if len(current) > 1:
            chains.append(current)

        current = []

    if len(current) > 1:
        chains.append(current)

    return chains
