import pytest

from tests.suite.playback import ReplayingTarget


@pytest.fixture(name="replaying_target")
def replaying_target_fixture() -> ReplayingTarget:
    return ReplayingTarget()
