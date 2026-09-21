import re
from pathlib import Path
from typing import Final, List, Set, Tuple

import pytest

from sampletones_shared.paths.source import REPOSITORY_ROOT

ENCODING: Final[str] = "utf-8"
LINK: Final[re.Pattern[str]] = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
HEADING: Final[re.Pattern[str]] = re.compile(r"^#{1,6}\s+(.*?)\s*$", re.MULTILINE)
EXTERNAL: Final[Tuple[str, ...]] = ("http://", "https://", "mailto:")
DOCUMENTATION: Final[Path] = REPOSITORY_ROOT / "docs"
INDEX: Final[Path] = DOCUMENTATION / "index.md"
ROOT_PAGES: Final[Tuple[str, ...]] = ("README.md", "CHANGELOG.md")


def anchor(heading: str) -> str:
    """The fragment GitHub gives a heading: punctuation dropped, every remaining space a hyphen."""
    text = re.sub(r"[`*]", "", heading).strip().lower()
    return re.sub(r"[^\w\s-]", "", text).replace(" ", "-")


def text(page: Path) -> str:
    """The page as it is stored, which is UTF-8 whatever encoding the platform prefers."""
    return page.read_text(encoding=ENCODING)


def anchors(page: Path) -> Set[str]:
    return {anchor(heading) for heading in HEADING.findall(text(page))}


def pages() -> List[Path]:
    return sorted(DOCUMENTATION.rglob("*.md")) + [REPOSITORY_ROOT / name for name in ROOT_PAGES]


def identifier(page: Path) -> str:
    return page.relative_to(REPOSITORY_ROOT).as_posix()


class TestEveryInternalLinkResolves:
    """A link between documents names a file that exists and, where it names one, a heading it holds."""

    @pytest.mark.parametrize("page", pages(), ids=identifier)
    def test_the_page_links_only_to_files_and_headings_that_exist(self, page: Path) -> None:
        for target in LINK.findall(text(page)):
            if target.startswith(EXTERNAL):
                continue

            path, _, fragment = target.partition("#")
            destination = (page.parent / path).resolve() if path else page
            assert destination.exists(), f"{identifier(page)} links to a missing file: {target}"

            if fragment and destination.suffix == ".md":
                assert fragment in anchors(destination), f"{identifier(page)} links to a missing heading: {target}"


class TestTheIndexListsEveryDocument:
    """`docs/index.md` is the map of the documentation, so a page is reachable from it."""

    def test_every_page_is_listed(self) -> None:
        listed = {(INDEX.parent / target.partition("#")[0]).resolve() for target in LINK.findall(text(INDEX))}
        missing = [
            identifier(page) for page in DOCUMENTATION.rglob("*.md") if page != INDEX and page.resolve() not in listed
        ]

        assert not missing, f"documents missing from docs/index.md: {missing}"
