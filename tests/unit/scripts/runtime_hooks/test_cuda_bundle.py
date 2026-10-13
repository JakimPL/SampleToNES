import site
import sys
from pathlib import Path

import pytest

from tests.suite.scripts import load_script


class TestCudaBundleHook:
    def test_the_bundle_is_the_only_site_packages(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
        monkeypatch.setattr(site, "getsitepackages", site.getsitepackages)
        monkeypatch.setattr(site, "ENABLE_USER_SITE", site.ENABLE_USER_SITE)

        load_script("runtime_hooks/cuda_bundle.py")

        assert site.getsitepackages() == [str(tmp_path)]
        assert site.getsitepackages(["/elsewhere"]) == [str(tmp_path)]
        assert site.ENABLE_USER_SITE is False
