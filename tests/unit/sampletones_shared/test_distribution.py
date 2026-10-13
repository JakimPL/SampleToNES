import tomllib

import pytest

from sampletones_shared.distribution import DOCUMENTATION_LABEL, SAMPLETONES_DOCUMENTATION_ADDRESS, project_address
from sampletones_shared.paths.source import REPOSITORY_ROOT


class TestProjectAddress:
    def test_the_documentation_address_is_the_one_the_project_lists(self) -> None:
        with (REPOSITORY_ROOT / "pyproject.toml").open("rb") as stream:
            urls = tomllib.load(stream)["project"]["urls"]

        assert SAMPLETONES_DOCUMENTATION_ADDRESS == urls[DOCUMENTATION_LABEL]

    def test_an_unlisted_label_is_refused(self) -> None:
        with pytest.raises(KeyError):
            project_address("Nowhere")
