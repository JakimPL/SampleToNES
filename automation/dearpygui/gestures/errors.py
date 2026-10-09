class GestureLostError(AssertionError):
    """Raised when a gesture's input never reached the control it was aimed at."""


class SlowFramesError(GestureLostError):
    """Raised when the display draws its frames too slowly for Dear ImGui to read a gesture the way a person
    meant it.
    """
