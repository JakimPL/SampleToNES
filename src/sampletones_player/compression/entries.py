from sampletones_player.compression.tokens.span import token_span


def stream_entry(stream: bytes, tick: int) -> int:
    """The byte of ``stream`` the token covering ``tick`` begins at.

    A song that repeats re-enters its streams partway through, and what the driver needs to
    resume there is where each plane's next opcode lies. The encoder holds a token boundary at
    the tick a song returns to, so the walk lands on it exactly.

    Args:
        stream: The plane's token stream.
        tick: The tick the stream is re-entered at.

    Returns:
        int: The byte the token covering ``tick`` begins at, counted from the stream's own start.

    Raises:
        ValueError: If the stream spans ``tick`` rather than starting a token there.
    """
    position = 0
    reached = 0
    while reached < tick:
        span = token_span(stream, position)
        reached += span.ticks
        position += span.size

    if reached != tick:
        raise ValueError(f"the stream spans tick {tick} rather than starting a token there")

    return position
