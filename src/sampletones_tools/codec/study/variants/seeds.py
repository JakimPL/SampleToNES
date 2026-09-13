from typing import Final, List, Sequence, Tuple

from sampletones_player.compression.dictionary.phrase import Phrase

MIN_PIECE_LENGTH: Final[int] = 2


def trimmed(seeds: Sequence[Phrase]) -> Tuple[Phrase, ...]:
    """Every seed with its trailing plateau cut to one value.

    A token playing a phrase past its end holds the final value onward, so the ticks a body
    spends resting on its last value are ticks the token covers for free.

    Args:
        seeds: The phrases the song's instruments offer.

    Returns:
        Tuple[Phrase, ...]: The same phrases, each ending where its last value first appears.
    """
    return tuple(Phrase(body=_trimmed_body(seed.body)) for seed in seeds)


def split(
    seeds: Sequence[Phrase],
    threshold: int,
) -> Tuple[Phrase, ...]:
    """Every seed cut at the plateaus of at least ``threshold`` ticks it holds.

    A plateau inside a body is stored one byte per tick, where a token's count would cover the
    rest for free. Cutting the body where a plateau begins keeps the plateau's first value at
    the end of one piece, so the token playing that piece holds it, and the next piece starts
    where the body moves again.

    Args:
        seeds: The phrases the song's instruments offer.
        threshold: The ticks a plateau rests for before the body is cut there.

    Returns:
        Tuple[Phrase, ...]: The pieces, each of at least two values, in the order they are cut.
    """
    return tuple(Phrase(body=piece) for seed in seeds for piece in _pieces(seed.body, threshold))


def whole_and_split(
    seeds: Sequence[Phrase],
    threshold: int,
) -> Tuple[Phrase, ...]:
    """Every seed as it stands, followed by its pieces, for the encoder to weigh against each other.

    Args:
        seeds: The phrases the song's instruments offer.
        threshold: The ticks a plateau rests for before the body is cut there.

    Returns:
        Tuple[Phrase, ...]: The whole phrases, then the pieces.
    """
    return (*seeds, *split(seeds, threshold))


def _trimmed_body(body: bytes) -> bytes:
    end = len(body)
    while end > 1 and body[end - 1] == body[end - 2]:
        end -= 1

    return body[:end]


def _pieces(
    body: bytes,
    threshold: int,
) -> List[bytes]:
    pieces: List[bytes] = []
    current = bytearray()
    start = 0
    while start < len(body):
        end = start
        while end < len(body) and body[end] == body[start]:
            end += 1

        if end - start >= threshold:
            current.append(body[start])
            pieces.append(bytes(current))
            current = bytearray()
        else:
            current.extend(body[start:end])

        start = end

    if current:
        pieces.append(bytes(current))

    return [piece for piece in pieces if len(piece) >= MIN_PIECE_LENGTH]
