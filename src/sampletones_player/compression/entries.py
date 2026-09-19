from sampletones_player.compression.tokens.span import token_span


def stream_entry(stream: bytes, position: int) -> int:
    """The byte of ``stream`` the token covering the value at ``position`` begins at.

    A song that repeats re-enters its streams partway through, and what the driver needs to
    resume there is where each plane's next opcode lies. The encoder holds a token boundary at
    the position each plane stands at once the song returns, so the walk lands on it exactly.

    Args:
        stream: The plane's token stream.
        position: The value the stream is re-entered at.

    Returns:
        int: The byte the token covering ``position`` begins at, counted from the stream's own
            start.

    Raises:
        ValueError: If the stream spans ``position`` rather than starting a token there.
    """
    offset = 0
    reached = 0
    while reached < position:
        span = token_span(stream, offset)
        reached += span.ticks
        offset += span.size

    if reached != position:
        raise ValueError(f"the stream spans position {position} rather than starting a token there")

    return offset
