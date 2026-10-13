from pathlib import Path, PurePosixPath
from typing import Dict, Final

import pytest
from markdown_it import MarkdownIt

from assets.documentation.markdown.parser import markdown_parser
from assets.documentation.navigation import Navigation
from assets.documentation.pages.model import ParsedPage
from assets.documentation.pages.reader import parse_page
from assets.documentation.published import INDEX_PAGE, published_pages

ADDRESS: Final[str] = "https://example.com/project/docs"
VERSION: Final[str] = "1.2.3"

INDEX: Final[str] = """# Example documentation

An opening paragraph.

## Using it

- [Start here](guide/start.md) — the first steps.
- [Next steps](guide/next.md#second-part) — what follows.
- [Glossary](glossary.md)

## Development

- [Notes](development/notes.md)
"""

START: Final[str] = """# Start here

Before the first section.

## First part

See [the next part](next.md#second-part), [the guide](./), [the notes](../development/notes.md),
[this part](#first-part) and [the web](https://example.com).

<img src="../images/picture.webp" alt="A picture">

## First part

| Column | Value |
|---|---|
| one | 1 |
"""

NEXT: Final[str] = """# Next steps

## Second part

Text.
"""

GLOSSARY: Final[str] = """# Glossary

## Term

A word.
"""

NOTES: Final[str] = "# Notes\n"

PROJECT: Final[str] = f"""[project]
name = "example"
version = "{VERSION}"

[project.urls]
Documentation = "{ADDRESS}"
"""

DOCUMENTS: Final[Dict[str, str]] = {
    "index.md": INDEX,
    "glossary.md": GLOSSARY,
    "guide/start.md": START,
    "guide/next.md": NEXT,
    "development/notes.md": NOTES,
}
PICTURES: Final[Dict[str, bytes]] = {
    "images/picture.webp": b"picture",
    "images/unused.webp": b"unused",
}


@pytest.fixture
def docs(tmp_path: Path) -> Path:
    """A small docs folder: an index with a published and a development section, two guide pages,
    a glossary, a development page and two pictures, one of them shown."""
    root = tmp_path / "docs"
    for relative, text in DOCUMENTS.items():
        (root / relative).parent.mkdir(parents=True, exist_ok=True)
        (root / relative).write_text(text, encoding="utf-8")

    for relative, data in PICTURES.items():
        (root / relative).parent.mkdir(parents=True, exist_ok=True)
        (root / relative).write_bytes(data)

    return root


@pytest.fixture
def project(tmp_path: Path) -> Path:
    path = tmp_path / "pyproject.toml"
    path.write_text(PROJECT, encoding="utf-8")
    return path


@pytest.fixture
def parser() -> MarkdownIt:
    return markdown_parser()


@pytest.fixture
def pages(parser: MarkdownIt, docs: Path) -> Dict[PurePosixPath, ParsedPage]:
    return {relative: parse_page(parser, docs, relative) for relative in published_pages(docs)}


@pytest.fixture
def navigation(pages: Dict[PurePosixPath, ParsedPage]) -> Navigation:
    return Navigation.read(pages[INDEX_PAGE], pages)
