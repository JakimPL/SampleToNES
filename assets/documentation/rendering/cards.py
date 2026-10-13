from html import escape

from assets.documentation.pages.model import Section


def section_card(
    section: Section,
    glyph: str,
) -> str:
    """One section as the application's card: the header strip with the purpose glyph and the
    heading, then the section's prose. The opening section is a card without a header."""
    body = f'<div class="prose">\n{section.body_html}</div>'
    if section.title_html is None or section.anchor is None:
        return f'<section class="card">\n{body}\n</section>'

    header = (
        '<h2 class="card-header">'
        f'<span class="card-glyph">{escape(glyph)}</span>'
        f'<span class="card-title">{section.title_html}</span>'
        "</h2>"
    )
    return f'<section class="card" id="{escape(section.anchor)}">\n{header}\n{body}\n</section>'
