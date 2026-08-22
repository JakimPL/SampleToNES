from typing import Union

from sampletones_player.compression.tokens.hold import HoldToken
from sampletones_player.compression.tokens.literal import LiteralToken
from sampletones_player.compression.tokens.phrase import PhraseToken

TokenUnion = Union[HoldToken, LiteralToken, PhraseToken]
