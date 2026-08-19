import msgpack

from sampletones_core.compatibility.kind import ObjectKind
from sampletones_core.compatibility.upgrade import upgrade_binary
from sampletones_shared.application import (
    SAMPLETONES_LIBRARY_DATA_VERSION,
    SAMPLETONES_RECONSTRUCTION_DATA_VERSION,
)


class TestUpgradeBinary:
    def test_current_reconstruction_version_returns_the_same_bytes(self) -> None:
        binary = msgpack.packb(
            {"metadata": {"reconstruction_data_version": SAMPLETONES_RECONSTRUCTION_DATA_VERSION}},
            use_bin_type=True,
        )

        assert upgrade_binary(ObjectKind.RECONSTRUCTION, binary) is binary

    def test_current_library_version_returns_the_same_bytes(self) -> None:
        binary = msgpack.packb(
            {"metadata": {"library_data_version": SAMPLETONES_LIBRARY_DATA_VERSION}},
            use_bin_type=True,
        )

        assert upgrade_binary(ObjectKind.LIBRARY, binary) is binary

    def test_missing_metadata_returns_the_same_bytes(self) -> None:
        binary = msgpack.packb({"items": []}, use_bin_type=True)

        assert upgrade_binary(ObjectKind.RECONSTRUCTION, binary) is binary

    def test_non_mapping_payload_returns_the_same_bytes(self) -> None:
        binary = msgpack.packb([1, 2, 3], use_bin_type=True)

        assert upgrade_binary(ObjectKind.RECONSTRUCTION, binary) is binary

    def test_malformed_payload_returns_the_same_bytes(self) -> None:
        binary = b"\xc1"

        assert upgrade_binary(ObjectKind.RECONSTRUCTION, binary) is binary
