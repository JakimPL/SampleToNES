from typing import Any, Dict, Final

import msgpack
import numpy as np

from sampletones_core.compatibility.kind import ObjectKind
from sampletones_core.compatibility.upgrade import upgrade_binary
from sampletones_shared.application import (
    SAMPLETONES_LIBRARY_DATA_VERSION,
    SAMPLETONES_RECONSTRUCTION_DATA_VERSION,
)

FEATURE_EDGES: Final[bytes] = np.array([0.0, 10.0, 30.0], dtype=np.float32).tobytes()
FEATURE_VALUES: Final[bytes] = np.array([0.5, 3.0], dtype=np.float32).tobytes()
REPAIRED_VALUES: Final[np.ndarray] = np.array([0.06483728, 0.6872635], dtype=np.float32)


def _library_at_2_0(spectrum_method: str) -> Dict[str, Any]:
    return {
        "metadata": {"library_data_version": "2.0"},
        "config": {"spectrum_method": spectrum_method, "transformation_gamma": 100},
        "items": [{"fragment": {"feature": {"edges": FEATURE_EDGES, "values": FEATURE_VALUES}}}],
    }


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

    def test_reconstruction_upgrade_names_streams_by_channel_and_stamps(self) -> None:
        binary = msgpack.packb(
            {
                "metadata": {"reconstruction_data_version": "2.1"},
                "approximations_data": [{"generator_name": "pulse1", "approximation": [1.0, 2.0]}],
                "instructions_data": [],
                "config": {
                    "metadata": {"reconstruction_data_version": "2.1"},
                    "generation": {"generators": ["pulse1", "noise"]},
                },
            },
            use_bin_type=True,
        )

        upgraded = upgrade_binary(ObjectKind.RECONSTRUCTION, binary)
        data = msgpack.unpackb(upgraded, raw=False)

        assert data["approximations_data"][0]["channel_name"] == "pulse1"
        assert "generator_name" not in data["approximations_data"][0]
        assert "channels" not in data["config"]["generation"]
        assert data["stems_data"]["config"]["entries"][0]["settings"]["channels"] == ["pulse1", "noise"]
        assert data["config"]["metadata"]["reconstruction_data_version"] == SAMPLETONES_RECONSTRUCTION_DATA_VERSION
        assert data["metadata"]["reconstruction_data_version"] == SAMPLETONES_RECONSTRUCTION_DATA_VERSION

    def test_library_upgrade_restates_windowed_features_and_stamps(self) -> None:
        binary = msgpack.packb(_library_at_2_0("fft"), use_bin_type=True)

        data = msgpack.unpackb(upgrade_binary(ObjectKind.LIBRARY, binary), raw=False)

        repaired = np.frombuffer(data["items"][0]["fragment"]["feature"]["values"], dtype=np.float32)
        np.testing.assert_allclose(repaired, REPAIRED_VALUES, rtol=1e-6)
        assert data["metadata"]["library_data_version"] == SAMPLETONES_LIBRARY_DATA_VERSION

    def test_library_upgrade_stamps_a_constant_q_library_as_it_stands(self) -> None:
        binary = msgpack.packb(_library_at_2_0("cqt"), use_bin_type=True)

        data = msgpack.unpackb(upgrade_binary(ObjectKind.LIBRARY, binary), raw=False)

        assert data["items"][0]["fragment"]["feature"]["values"] == FEATURE_VALUES
        assert data["metadata"]["library_data_version"] == SAMPLETONES_LIBRARY_DATA_VERSION
