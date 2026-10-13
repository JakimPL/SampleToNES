from pathlib import Path, PurePosixPath
from typing import Final, List, Tuple

MARKDOWN_SUFFIX: Final[str] = ".md"
PAGE_SUFFIX: Final[str] = ".html"
INDEX_PAGE: Final[PurePosixPath] = PurePosixPath("index.md")
PUBLISHED_FOLDERS: Final[Tuple[str, ...]] = ("guide", "concepts", "tools", "formats", "api")
PUBLISHED_ROOT_PAGES: Final[Tuple[PurePosixPath, ...]] = (INDEX_PAGE, PurePosixPath("glossary.md"))


def is_published(relative: PurePosixPath) -> bool:
    """Whether a document, named relative to the docs folder, belongs to the user's documentation.

    The documentation carries what a user of the application reads: the index, the glossary, and
    the guide, concepts, tools, formats and API sections. The development section stays online.
    """
    if relative.suffix != MARKDOWN_SUFFIX:
        return False

    if len(relative.parts) == 1:
        return relative in PUBLISHED_ROOT_PAGES

    return relative.parts[0] in PUBLISHED_FOLDERS


def published_pages(docs: Path) -> List[PurePosixPath]:
    """Every published document under ``docs``, relative to it, in a stable order."""
    relatives = (PurePosixPath(path.relative_to(docs).as_posix()) for path in docs.rglob(f"*{MARKDOWN_SUFFIX}"))
    return sorted(relative for relative in relatives if is_published(relative))


def page_path(relative: PurePosixPath) -> PurePosixPath:
    """The page a document becomes, at the same place in the site as the document in the docs."""
    return relative.with_suffix(PAGE_SUFFIX)
