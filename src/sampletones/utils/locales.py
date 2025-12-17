import locale

PREFERRED_ENCODING = locale.getpreferredencoding(False)


def to_utf8(name: str) -> str:
    try:
        return name.encode(PREFERRED_ENCODING).decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return name
