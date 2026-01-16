import locale

PREFERRED_ENCODING = locale.getpreferredencoding(False)


def to_utf8(name: str, encoding: str = PREFERRED_ENCODING) -> str:
    """
    Converts a string from the specified encoding to UTF-8.

    This function is primarily used to convert device names from audio libraries,
    which typically use the system's preferred encoding. It safely handles strings
    that may already be in UTF-8 or contain characters that cannot be converted.

    Args:
        name (str): The string to convert to UTF-8.
        encoding (str): The source encoding of the string. Defaults to the system's
                       preferred encoding.

    Returns:
        str: The string converted to UTF-8. If conversion fails due to encoding
             errors, returns the original string unchanged.

    Examples:
        >>> to_utf8(r"Device Name", "latin-1")
        'Device Name'
        >>> to_utf8("GĹ‚oĹ›nik", "cp1250")
        'Głośnik'
    """
    try:
        return name.encode(encoding).decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return name
