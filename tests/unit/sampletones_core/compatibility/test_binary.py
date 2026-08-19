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

    def test_reconstruction_upgrade_renames_channels_and_stamps(self) -> None:
        binary = msgpack.packb(
            {
                "metadata": {"reconstruction_data_version": "2.1"},
                "approximations_data": [{"generator_name": "pulse1", "approximation": [1.0, 2.0]}],
                "instructions_data": [],
                "config": {"generation": {"generators": ["pulse1", "noise"]}},
            },
            use_bin_type=True,
        )

        upgraded = upgrade_binary(ObjectKind.RECONSTRUCTION, binary)
        data = msgpack.unpackb(upgraded, raw=False)

        assert data["approximations_data"][0]["channel_name"] == "pulse1"
        assert "generator_name" not in data["approximations_data"][0]
        assert data["config"]["generation"]["channels"] == ["pulse1", "noise"]
        assert data["metadata"]["reconstruction_data_version"] == SAMPLETONES_RECONSTRUCTION_DATA_VERSION
