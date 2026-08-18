from pathlib import Path

import pytest

from tests.suite.browser import BrowserCorpus, build_corpus


@pytest.fixture
def corpus(tmp_path: Path) -> BrowserCorpus:
    """The reconstructions directory the browser tests read, as both views shape it."""
    return build_corpus(tmp_path)
