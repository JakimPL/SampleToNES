from pathlib import Path
from typing import Final, List

import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, SpectrumMethod
from sampletones_tools.calibration.fingerprint import (
    ResumeRefusedError,
    check_resumable,
    fingerprint_of,
    write_fingerprint,
)
from sampletones_tools.calibration.runner import CalibrationVariant, build_variants

from .conversions import item_named

CHANNELS: Final[List[ChannelName]] = [ChannelName.PULSE1]


def _variants(method: SpectrumMethod) -> List[CalibrationVariant]:
    return build_variants(Config(), [method], [1.0], [])


class TestCheckResumable:
    def test_a_run_measuring_alike_resumes(self, tmp_path: Path) -> None:
        fingerprint = fingerprint_of(_variants(SpectrumMethod.FFT), [item_named("a", listed=True)], CHANNELS)
        write_fingerprint(tmp_path, fingerprint)

        check_resumable(tmp_path, fingerprint)

    def test_a_folder_without_a_run_is_refused(self, tmp_path: Path) -> None:
        fingerprint = fingerprint_of(_variants(SpectrumMethod.FFT), [item_named("a", listed=True)], CHANNELS)

        with pytest.raises(ResumeRefusedError, match="holds no run"):
            check_resumable(tmp_path, fingerprint)

    def test_a_run_of_other_sounds_is_refused_naming_them(self, tmp_path: Path) -> None:
        variants = _variants(SpectrumMethod.FFT)
        write_fingerprint(tmp_path, fingerprint_of(variants, [item_named("a", listed=True)], CHANNELS))

        with pytest.raises(ResumeRefusedError, match="measured other sounds"):
            check_resumable(tmp_path, fingerprint_of(variants, [item_named("a", listed=False)], CHANNELS))
