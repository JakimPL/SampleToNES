import pytest

from sampletones_application.utils.palette.catalog import DEFAULT_PALETTE_NAME
from sampletones_tools.web.design import ApplicationDesign


@pytest.fixture(scope="module")
def design() -> ApplicationDesign:
    return ApplicationDesign.load(DEFAULT_PALETTE_NAME)
