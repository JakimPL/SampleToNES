from sampletones_shared.constants.symbols import TITLE_SEPARATOR


def join_segments(*segments: str) -> str:
    """Join the segments that carry text with the shared title separator.

    The single place a title separator is written, so every composed title reads the same
    and stays within the characters a window title bar renders on every platform.
    """
    return TITLE_SEPARATOR.join(segment for segment in segments if segment)


def window_title(application_name: str, document: str) -> str:
    """Compose the window title from the application name and the document on screen.

    The application name leads, so the window is identifiable while a document is open and
    while the workspace is empty.
    """
    return join_segments(application_name, document)
