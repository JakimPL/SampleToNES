import posixpath
import shutil
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from shutil import copyfile
from string import Template
from typing import Final, Iterable, List, Set

from markdown_it import MarkdownIt
from markdown_it.utils import EnvType

from assets.documentation.links.resolver import EXTERNAL_PREFIXES, BrokenLinkError, LinkResolver
from assets.documentation.markdown.parser import markdown_parser
from assets.documentation.navigation import Navigation
from assets.documentation.pages.model import ParsedPage
from assets.documentation.pages.reader import parse_page
from assets.documentation.pages.sections import image_sources, split_sections
from assets.documentation.paths import STATIC_DIRECTORY
from assets.documentation.project import ProjectFacts
from assets.documentation.published import INDEX_PAGE, page_path, published_pages
from assets.documentation.rendering.cards import section_card
from assets.documentation.rendering.navigation import navigation_html
from assets.documentation.rendering.page import LAYOUT_DIRECTORY, PageChrome, PageContent, render_page
from sampletones_application.utils.palette.catalog import DEFAULT_PALETTE_NAME
from sampletones_shared.documentation.site import DocumentationSite
from sampletones_tools.web.design import ApplicationDesign
from sampletones_tools.web.writer import write_layout

TEMPLATE_FILE: Final[str] = "page.html"
DOCUMENTATION_STYLESHEET: Final[str] = "documentation.css"
TEXT_NEWLINE: Final[str] = "\n"
PARENT: Final[str] = ".."


class OutputOccupiedError(ValueError):
    pass


@dataclass(frozen=True)
class SiteRequest:
    """Where the documentation is read from and where its site is written.

    Attributes:
        docs: The docs folder of a checkout.
        project: The checkout's ``pyproject.toml``, for the version and the online address.
        output: The folder the site is written into; empty, or holding an earlier site.
    """

    docs: Path
    project: Path
    output: Path


def build_site(request: SiteRequest) -> DocumentationSite:
    """Write the user's documentation as HTML pages in the application's look.

    Every published document becomes a page at the same place in the site, wearing the web
    layout in the application's default palette, with the navigation the docs index lays out. The
    pictures the pages show are copied beside them, and the site is sealed with its stamp last.

    Raises:
        OutputOccupiedError: If the output holds files other than an earlier site.
        BrokenLinkError: If a page links to a missing document, heading or picture.
    """
    _prepare(request.output)
    facts = ProjectFacts.read(request.project)
    parser = markdown_parser()
    pages = {relative: parse_page(parser, request.docs, relative) for relative in published_pages(request.docs)}
    navigation = Navigation.read(pages[INDEX_PAGE], pages)
    resolver = LinkResolver(
        request.docs,
        {relative: page.anchors for relative, page in pages.items()},
        navigation.folder_pages,
        facts.documentation_address,
    )
    design = ApplicationDesign.load(DEFAULT_PALETTE_NAME)
    layout = request.output / LAYOUT_DIRECTORY
    stylesheets = write_layout(layout, design)
    copyfile(STATIC_DIRECTORY / DOCUMENTATION_STYLESHEET, layout / DOCUMENTATION_STYLESHEET)
    chrome = PageChrome(
        version=facts.version,
        address=facts.documentation_address,
        stylesheets=(*stylesheets, DOCUMENTATION_STYLESHEET),
    )
    template = Template((STATIC_DIRECTORY / TEMPLATE_FILE).read_text(encoding="utf-8"))
    pictures: Set[PurePosixPath] = set()
    for page in pages.values():
        _resolve_links(page, resolver)
        html = _page_html(parser, template, chrome, navigation, page, design.glyphs.common.tick)
        target = request.output / page_path(page.relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html, encoding="utf-8", newline=TEXT_NEWLINE)
        pictures.update(_pictures(request.docs, page))

    _copy_pictures(request.docs, request.output, pictures)
    site = DocumentationSite(request.output)
    site.write_stamp()
    return site


def _prepare(output: Path) -> None:
    site = DocumentationSite(output)
    if output.exists() and any(output.iterdir()):
        if site.read_stamp() is None:
            raise OutputOccupiedError(f"{output} holds files other than a documentation site; give an empty folder")

        shutil.rmtree(output)

    output.mkdir(parents=True, exist_ok=True)


def _resolve_links(
    page: ParsedPage,
    resolver: LinkResolver,
) -> None:
    for token in page.tokens:
        for child in token.children or []:
            href = child.attrGet("href") if child.type == "link_open" else None
            if href is not None:
                child.attrSet("href", resolver.resolve(str(href), page.relative))


def _page_html(
    parser: MarkdownIt,
    template: Template,
    chrome: PageChrome,
    navigation: Navigation,
    page: ParsedPage,
    glyph: str,
) -> str:
    env: EnvType = {}

    def inline(text: str) -> str:
        return str(parser.renderInline(text, env))

    sections = split_sections(parser, page.tokens, env)
    content = PageContent(
        relative=page.relative,
        title_html=inline(page.title),
        navigation_html=navigation_html(navigation, page.relative, sections, inline),
        cards_html="\n".join(section_card(section, glyph) for section in sections),
    )
    return render_page(template, chrome, content)


def _pictures(
    docs: Path,
    page: ParsedPage,
) -> List[PurePosixPath]:
    pictures: List[PurePosixPath] = []
    for source in image_sources(page.tokens):
        if source.startswith(EXTERNAL_PREFIXES):
            continue

        target = posixpath.normpath(posixpath.join(page.relative.parent.as_posix(), source))
        if target.startswith(PARENT) or not (docs / target).is_file():
            raise BrokenLinkError(f"{page.relative} shows a picture outside the docs or missing: {source}")

        pictures.append(PurePosixPath(target))

    return pictures


def _copy_pictures(
    docs: Path,
    output: Path,
    pictures: Iterable[PurePosixPath],
) -> None:
    for picture in sorted(pictures):
        target = output / picture
        target.parent.mkdir(parents=True, exist_ok=True)
        copyfile(docs / picture, target)
