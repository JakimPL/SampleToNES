from typing import Final, Mapping, Tuple

MPEG_1_LADDER: Final[Mapping[int, float]] = {
    320: 0.05,
    256: 0.19,
    224: 0.33,
    192: 0.44,
    160: 0.55,
    128: 0.65,
    112: 0.72,
    96: 0.78,
    80: 0.83,
    64: 0.88,
    56: 0.91,
    48: 0.94,
    40: 0.97,
    32: 0.99,
}

MPEG_2_LADDER: Final[Mapping[int, float]] = {
    160: 0.02,
    144: 0.10,
    128: 0.21,
    112: 0.31,
    96: 0.42,
    80: 0.52,
    64: 0.62,
    56: 0.68,
    48: 0.73,
    40: 0.78,
    32: 0.84,
    24: 0.89,
    16: 0.94,
    8: 0.98,
}

MPEG_2_5_LADDER: Final[Mapping[int, float]] = {
    64: 0.03,
    56: 0.13,
    48: 0.27,
    40: 0.41,
    32: 0.56,
    24: 0.70,
    16: 0.84,
    8: 0.96,
}

MP3_LADDERS: Final[Mapping[int, Mapping[int, float]]] = {
    8000: MPEG_2_5_LADDER,
    16000: MPEG_2_LADDER,
    22050: MPEG_2_LADDER,
    44100: MPEG_1_LADDER,
    48000: MPEG_1_LADDER,
}

MP3_SAMPLE_RATES: Final[Tuple[int, ...]] = tuple(sorted(MP3_LADDERS))
PREFERRED_MP3_BITRATE: Final[int] = 192


def mp3_bitrates(sample_rate: int) -> Tuple[int, ...]:
    """The bitrates MP3 encodes at ``sample_rate``, highest first.

    Each MPEG audio version defines its own ladder of bitrates and covers its own set of sample
    rates, so the choice on offer narrows as the rate drops: the full ladder up to 320 kbps at
    44100 and 48000 Hz, a ladder topping out at 160 kbps at 16000 and 22050 Hz, and one topping
    out at 64 kbps at 8000 Hz.

    Args:
        sample_rate: The rate the file is written at.

    Returns:
        Tuple[int, ...]: The bitrates in kbps, highest first.

    Raises:
        KeyError: If MP3 does not encode at ``sample_rate``.
    """
    return tuple(MP3_LADDERS[sample_rate])


def mp3_compression_level(sample_rate: int, bitrate: int) -> float:
    """The encoder setting that reaches ``bitrate`` at ``sample_rate``.

    libsndfile asks for MP3 quality as a compression level between 0 and 1 and turns that into a
    rung on the ladder its MPEG version defines, so the level standing for a given bitrate depends
    on the sample rate as well. Each level here sits in the middle of the band that selects its
    rung, which leaves room either side for the rounding an encoder build applies.

    Args:
        sample_rate: The rate the file is written at.
        bitrate: The bitrate in kbps, one of those :func:`mp3_bitrates` reports.

    Returns:
        float: The compression level to open the file with.

    Raises:
        KeyError: If MP3 does not encode at ``sample_rate``, or does not reach ``bitrate`` there.
    """
    return MP3_LADDERS[sample_rate][bitrate]


def default_mp3_bitrate(sample_rate: int) -> int:
    """The bitrate a render starts at: the preferred one where the rate reaches it, else its best.

    Args:
        sample_rate: The rate the file is written at.

    Returns:
        int: The bitrate in kbps.

    Raises:
        KeyError: If MP3 does not encode at ``sample_rate``.
    """
    bitrates = mp3_bitrates(sample_rate)
    return next(
        (bitrate for bitrate in bitrates if bitrate <= PREFERRED_MP3_BITRATE),
        bitrates[-1],
    )
