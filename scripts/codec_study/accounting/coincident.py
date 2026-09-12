from typing import Final, Mapping, Sequence

from codec_study.accounting.finding import NOTHING, Finding
from codec_study.accounting.tokens import ReadToken
from sampletones_player.compression.planes.order import PlaneOrder
from sampletones_player.specification.compression import OPCODE_SIZE

CONTROL_SUFFIX: Final[str] = "_control"
VALUE_SUFFIX: Final[str] = "_value"


def coincident_starts(tokens: Mapping[str, Sequence[ReadToken]]) -> Finding:
    """What one opcode for a channel's control and value would spare where both start a token
    on the same tick (H5).

    A note usually changes its timbre and its pitch on the same tick, so the two planes pay two
    opcodes for one moment. One opcode announcing both is the bound stated here: a byte per
    coincidence, before the cost of telling the two apart.

    Args:
        tokens: Every plane's tokens, under the plane's name in the song block.

    Returns:
        Finding: The opcode bytes at coincident starts, and the bytes one opcode would spare.
    """
    finding = NOTHING
    for name in PlaneOrder.names():
        if not name.endswith(CONTROL_SUFFIX):
            continue

        channel = name.removesuffix(CONTROL_SUFFIX)
        control = {token.tick for token in tokens[name]}
        value = {token.tick for token in tokens[f"{channel}{VALUE_SUFFIX}"]}
        shared = len(control & value)
        finding += Finding(2 * OPCODE_SIZE * shared, OPCODE_SIZE * shared)

    return finding
