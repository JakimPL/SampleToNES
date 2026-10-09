import pytest

from tests.suite.frames import DrawnFrames


@pytest.fixture
def frames() -> DrawnFrames:
    """The frames a stems list settles on, which a case renders for itself.

    A frame a case renders is one the list stood on screen in, the way a list a reader is looking
    at is drawn; a case standing a list away says so on the frames before rendering them.
    """
    return DrawnFrames()
