from __future__ import annotations

import posixpath
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Dict, Final, List, Mapping, Optional, Tuple

from assets.documentation.pages.model import ParsedPage

GROUP_LEVEL: Final[str] = "h2"
FRAGMENT_SEPARATOR: Final[str] = "#"


@dataclass(frozen=True)
class NavigationEntry:
    page: PurePosixPath
    title: str


@dataclass(frozen=True)
class NavigationGroup:
    title: str
    entries: Tuple[NavigationEntry, ...]


@dataclass(frozen=True)
class Navigation:
    """The site's contents as the docs index lays them out: each of its sections a group, and each
    published document it links an entry, in the order the index names them.

    A section that links no published document, such as the development one, makes no group.
    """

    groups: Tuple[NavigationGroup, ...]

    @classmethod
    def read(
        cls,
        index: ParsedPage,
        pages: Mapping[PurePosixPath, ParsedPage],
    ) -> Navigation:
        groups: List[NavigationGroup] = []
        title: Optional[str] = None
        entries: Dict[PurePosixPath, NavigationEntry] = {}
        tokens = index.tokens
        for position, token in enumerate(tokens):
            if token.type == "heading_open" and token.tag == GROUP_LEVEL:
                cls._close(groups, title, entries)
                title, entries = tokens[position + 1].content, {}
            elif token.type == "inline" and title is not None:
                for child in token.children or []:
                    href = child.attrGet("href") if child.type == "link_open" else None
                    target = cls._target(index, str(href)) if href is not None else None
                    if target is not None and target in pages and target != index.relative:
                        entries.setdefault(target, NavigationEntry(page=target, title=pages[target].title))

        cls._close(groups, title, entries)
        return cls(groups=tuple(groups))

    @property
    def folder_pages(self) -> Dict[str, PurePosixPath]:
        """The first page the navigation lists in each folder, where a link to the folder leads."""
        firsts: Dict[str, PurePosixPath] = {}
        for group in self.groups:
            for entry in group.entries:
                if len(entry.page.parts) > 1:
                    firsts.setdefault(entry.page.parts[0], entry.page)

        return firsts

    @staticmethod
    def _target(
        index: ParsedPage,
        href: str,
    ) -> Optional[PurePosixPath]:
        path = href.partition(FRAGMENT_SEPARATOR)[0]
        if not path:
            return None

        return PurePosixPath(posixpath.normpath(posixpath.join(index.relative.parent.as_posix(), path)))

    @staticmethod
    def _close(
        groups: List[NavigationGroup],
        title: Optional[str],
        entries: Dict[PurePosixPath, NavigationEntry],
    ) -> None:
        if title is not None and entries:
            groups.append(NavigationGroup(title=title, entries=tuple(entries.values())))
