from typing import Any, Dict, Final

import pytest
from pydantic import ValidationError

from sampletones_tools.calibration.config.samples import SampleReference, SamplesConfig

REFERENCE: Final[Dict[str, Any]] = {
    "name": "sample",
    "url": "https://example.org/sample.wav",
    "file_name": "sample.wav",
    "sha256": "0" * 64,
    "start_seconds": 1.0,
    "end_seconds": 2.0,
    "license": "CC0 1.0",
    "attribution": "someone",
}


class TestSampleReference:
    def test_a_window_ending_before_it_starts_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="must end after it starts"):
            SampleReference.model_validate({**REFERENCE, "end_seconds": 0.5})


class TestSamplesConfig:
    def test_the_packaged_references_read(self) -> None:
        assert SamplesConfig.load().samples
