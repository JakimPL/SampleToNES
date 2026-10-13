from assets.documentation.pages.model import Section
from assets.documentation.rendering.cards import section_card

GLYPH = "▍"


class TestSectionCard:
    def test_a_section_wears_the_header_strip(self) -> None:
        card = section_card(
            Section(title_html="The <code>.nsf</code> file", anchor="the-nsf-file", body_html="<p>Text.</p>\n"), GLYPH
        )

        assert card.startswith('<section class="card" id="the-nsf-file">')
        assert f'<span class="card-glyph">{GLYPH}</span>' in card
        assert '<span class="card-title">The <code>.nsf</code> file</span>' in card
        assert '<div class="prose">\n<p>Text.</p>\n</div>' in card

    def test_the_opening_is_a_card_without_a_header(self) -> None:
        card = section_card(Section(title_html=None, anchor=None, body_html="<p>Opening.</p>\n"), GLYPH)

        assert card.startswith('<section class="card">')
        assert "card-header" not in card
