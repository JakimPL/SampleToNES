from typing import Final

import pytest

from sampletones_core.data import Metadata, MetadataContract
from sampletones_shared.exceptions import IncompatibleProjectVersionError, InvalidMetadataError

EXPECTED_VERSION: Final[str] = "1.1"
SPELLED_IN_FULL: Final[str] = "1.1.0"
OLDER_VERSION: Final[str] = "1.0"
NEWER_VERSION: Final[str] = "2.0"
FOREIGN_APPLICATION: Final[str] = "Another tracker"


@pytest.fixture(name="contract")
def contract_fixture() -> MetadataContract:
    """A contract accepting one version and refusing any other with a project's error."""
    return MetadataContract(
        label="Project data",
        expected_version=EXPECTED_VERSION,
        error=IncompatibleProjectVersionError,
    )


class TestValidateVersion:
    def test_the_expected_version_passes(self, contract: MetadataContract) -> None:
        contract.validate_version(EXPECTED_VERSION)

    def test_the_expected_version_spelled_in_full_passes(self, contract: MetadataContract) -> None:
        contract.validate_version(SPELLED_IN_FULL)

    @pytest.mark.parametrize("actual_version", [OLDER_VERSION, NEWER_VERSION])
    def test_another_version_is_refused_naming_both(self, contract: MetadataContract, actual_version: str) -> None:
        with pytest.raises(IncompatibleProjectVersionError) as refused:
            contract.validate_version(actual_version)

        assert (refused.value.actual_version, refused.value.expected_version) == (
            actual_version,
            EXPECTED_VERSION,
        )


class TestValidate:
    """The full check holds the writer first and then the version, through the same version rule."""

    def test_a_file_this_application_wrote_at_the_expected_version_passes(self, contract: MetadataContract) -> None:
        contract.validate(Metadata(), EXPECTED_VERSION)

    def test_a_file_at_another_version_is_refused_for_its_version(self, contract: MetadataContract) -> None:
        with pytest.raises(IncompatibleProjectVersionError) as refused:
            contract.validate(Metadata(), OLDER_VERSION)

        assert refused.value.actual_version == OLDER_VERSION

    def test_a_file_another_application_wrote_is_refused_before_its_version(self, contract: MetadataContract) -> None:
        with pytest.raises(InvalidMetadataError):
            contract.validate(Metadata(application_name=FOREIGN_APPLICATION), OLDER_VERSION)
