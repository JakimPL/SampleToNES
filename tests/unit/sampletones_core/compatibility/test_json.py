import json

from sampletones_core.compatibility.kind import ObjectKind
from sampletones_core.compatibility.upgrade import upgrade_json
from sampletones_shared.application import SAMPLETONES_PROJECT_DATA_VERSION


class TestUpgradeJson:
    def test_current_version_returns_the_same_bytes(self) -> None:
        raw = json.dumps({"format_version": SAMPLETONES_PROJECT_DATA_VERSION}).encode("utf-8")

        assert upgrade_json(ObjectKind.PROJECT, raw) is raw

    def test_missing_version_returns_the_same_bytes(self) -> None:
        raw = json.dumps({"samples": []}).encode("utf-8")

        assert upgrade_json(ObjectKind.PROJECT, raw) is raw

    def test_non_mapping_document_returns_the_same_bytes(self) -> None:
        raw = b"[1, 2, 3]"

        assert upgrade_json(ObjectKind.PROJECT, raw) is raw

    def test_malformed_document_returns_the_same_bytes(self) -> None:
        raw = b"{ not valid json"

        assert upgrade_json(ObjectKind.PROJECT, raw) is raw
